import os, sys, signal, time
import threading, collections, copy
import pyaudio, wave, snowboydetect

from log import Log

TOP_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCE_FILE = os.path.join(TOP_DIR, "resources/common.res")

class RingBuffer(object):
	_total_length=0
	_length=0

	"""
	Ring buffer to hold audio from PortAudio, from the Snowboy project

	:param Int size: number of bytes to store in the buffer.
	"""
	def __init__(self, size=4096):
		self._buf = collections.deque(maxlen=size)

	def extend(self, data):
		"""Adds data to the end of buffer"""
		self._buf.extend(data)
		length = len(data)
		self._length += length
		self._total_length += length

	def clear(self):
		"""Clear the buffer"""
		self._buf.clear()
		self._length = 0

	def get_copy(self):
		"""Retrieves a copy of the data of the buffer"""
		return copy.deepcopy(bytes(bytearray(self._buf)))

	def get(self):
		"""Retrieves data from the beginning of buffer and clears it"""
		tmp = bytes(bytearray(self._buf))
		self.clear()
		return tmp

	def length(self):
		"""Retrieves the length of data in the buffer"""
		return self._length

	def total_length(self):
		"""Retrieves the length of data ever put in the buffer"""
		return self._total_length

	def max_length(self):
		"""Retrieves the maximum length of data ever put in the buffer"""
		return self._buf.maxlen

class DetectorRingBuffer(RingBuffer):
	"""
	Ring buffer to hold audio from PortAudio, from the Snowboy project

	:param Int size: number of bytes to store in the buffer.
	"""

class InstanceBuffer(RingBuffer):
	_tag = "back_buffer"

	"""
	Ring buffer to hold audio from PortAudio, from the Snowboy project

	:param int num_channels: number of audio channels to write.
	:param int sample_rate: sample rate
	:param int bytes_per_sample: bytes per sample
	:param int record_for: seconds to record in the back buffer.
	"""
	def __init__(self,
		num_channels=1,
		sample_rate=16000,
		bytes_per_sample=2,
		record_for=60):
		self._bytes_per_second=num_channels*sample_rate*bytes_per_sample
		self._size=record_for*self._bytes_per_second
		self._buf = collections.deque(maxlen=self._size)

class BackwardBuffer(InstanceBuffer):
	_tag = "backward_buffer"

class ForwardBuffer(InstanceBuffer):
	_tag = "forward_buffer"
	_stop_capture = False

	def capture_stopped(self):
		"""Stopped extending the buffer with new data?"""
		return self._stop_capture

	def stop_capture(self):
		"""Stop extending the buffer with new data"""
		self._stop_capture = True

	def extend(self, data):
		"""Adds data to the end of buffer"""
		if not self._stop_capture:
			return super(ForwardBuffer, self).extend(data)

class InstanceRecorder(object):
	_tag = "instance_record"

	"""
	Object to handle file writing that records an instance of hotword use.

	:param BackwardBuffer buf_before: buffer of audio to prepend to WAV file.
	:param ForwarRingBuffer buf_after: buffer of audio to append to WAV file.
	:param int num_channels: number of audio channels to write.
	:param int sample_rate: sample rate.
	:param int bytes_per_sample: bytes per sample.
	:param dir: directory to save files to
	:param String file_prefix: prefix of files to save to.
	"""
	def __init__(self,
		buf_before,
		buf_after,
		num_channels=1,
		sample_rate=16000,
		bytes_per_sample=2,
		dir=TOP_DIR,
		file_prefix="recording-"):
		self.buf_before=buf_before
		self.buf_after=buf_after
		self._bytes_per_second=num_channels*sample_rate*bytes_per_sample
		self._file_prefix=file_prefix

		self.clean_up = False
		self._will_stop_capture=False
		self._actual_before_length=buf_before.length()/self._bytes_per_second
		self._desired_after_length=buf_after.max_length()/self._bytes_per_second
		self._desired_length=self._actual_before_length+self._desired_after_length
		Log.debug(self._tag, "Will record for %d (%d before, %f after)" % (self._desired_length, self._actual_before_length, self._desired_after_length))

		# File setup
		self.filename =  "%s%d.wav" % (self._file_prefix, int(time.time()))
		self._file = wave.open(os.path.join(dir, self.filename), "w")
		self._file.setnchannels(num_channels)
		self._file.setframerate(sample_rate)
		self._file.setsampwidth(bytes_per_sample)

	def start(self):
		"""
		Start writing the file from the buffers in a seperate thread.
		"""
		self._thread = threading.Thread(target=self.run)
		self._thread.daemon = True
		self._thread.start()

	def stop_capture(self):
		"""
		Stop capturing audio once enough has been captured.
		"""
		self._will_stop_capture=True
		captured_after_length=self.buf_after.total_length()/self._bytes_per_second

		while captured_after_length < self._desired_after_length:
			Log.warning(self._tag, "Will stop capture when captured enough data (%.2f/%.2f)" % (captured_after_length, self._desired_after_length))
			time.sleep((self._desired_after_length-captured_after_length/10))
			captured_after_length=self.buf_after.total_length()/self._bytes_per_second

		self.buf_after.stop_capture()
		Log.debug(self._tag, "Capture stopped with enough data (%.2f/%.2f)" % (captured_after_length, self._desired_after_length))

	def capture_stopped(self):
		"""Stopped extending the buffer with new data (or will stop)"""
		return self._will_stop_capture

	def extend_desired_length(self,desired_length):
		"""
		Extend the desired length of recording after the hotword to include the 
		next "desired_length" time.

		:param int desired_length: new desired length
		"""
		captured_after_length=self.buf_after.total_length()/self._bytes_per_second
		self._desired_after_length=captured_after_length+desired_length
		new_desired_length=self._actual_before_length+self._desired_after_length
		Log.debug(self._tag, "Extend designed length to %ds from now, from a total of %ds to %ds" % (desired_length, self._desired_length, new_desired_length))
		Log.debug(self._tag, "Currently captured %ds, written %ds" % (self._actual_before_length+captured_after_length, self._time_written))
		self._desired_length=new_desired_length

	def extend(self, data):
		"""Extend the forward buffer"""
		return self.buf_after.extend(data)

	def interrupt(self):
		"""
		Interrupt writing.
		"""
		Log.debug(self._tag, "Interrupt triggered")
		self._is_writing_interrupted = True

	def run(self):
		"""
		Start writing the file from the buffers in this thread.
		"""
		self._is_writing_interrupted = False

		# copy back buffer
		buf_before = self.buf_before.get_copy()
		self._buf_before_length=len(buf_before) / self._bytes_per_second
		self._file.writeframes("".join(buf_before))
		buf_before = None
		self._time_written = self._buf_before_length
		Log.debug(self._tag,
			"Writen %.2f seconds from before the hotword" % self._buf_before_length)

		# copy forward buffer
		while True:
			if self._is_writing_interrupted:
				Log.debug(self._tag, "Interrupt detected")
				break

			bytes = self.buf_after.get()
			self._file.writeframes("".join(bytes))

			additional_time_written = (len(bytes) / self._bytes_per_second)
			Log.debug(self._tag, "Written %.2f seconds" % additional_time_written)
			self._time_written += additional_time_written

			if self.buf_after.capture_stopped() and self.buf_after.length() == 0:
				break

			time.sleep(3)

		self._file.close()
		Log.debug(self._tag, "Written %.2f seconds of audio in %s" % (self._time_written, self.filename))
		self.clean_up = True
