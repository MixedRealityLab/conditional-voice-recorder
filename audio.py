import os, sys, signal, time
import threading, collections, copy
import pyaudio, wave, snowboydetect

from log import Log
from recorder import *

ADD_TO_RECORD_AFTER=2

class AudioHandler(object):
    _tag = "audio_handler"

    instance_recorders = []

    """Main detector object, based on `snowboydecoder.py` from Snowboy. Snowboy 
    decoder to detect whether a keyword specified by `decoder_model` exists in a 
    microphone input stream.

    :param decoder_model: decoder model file path; stirng or list of strings
    :param Path resource: resource file path.
    :param sensitivity: decoder sensitivity, a float of a list of floats.
                              The bigger the value, the more senstive the
                              decoder. If an empty list is provided, then the
                              default sensitivity in the model will be used.
    :param audio_gain: multiply input volume by this factor.
    :param bool continue_recording: continue recording on repeated utterances of
                                of the hotword.
    :param string output_dir: Directory to save recordings to.
    :param bool delete_active_recording: Delete an active recording if 
                                interrupted
    """
    def __init__(self,
        decoder_model,
        resource=RESOURCE_FILE,
        sensitivity=[],
        audio_gain=1,
        continue_recording=False,
        output_dir=".",
        delete_active_recording=False):

        self.is_running = False
        self.is_interrupted = False
        self.is_recording = False
        self.is_terminated = False

        self._start_recording_callback = None
        self._continue_recording_callback = None
        self._stop_recording_callback = None

        # Setup Snowboy
        tm = type(decoder_model)
        ts = type(sensitivity)
        if tm is not list:
            decoder_model = [decoder_model]
        if ts is not list:
            sensitivity = [sensitivity]
        model_str = ",".join(decoder_model)

        self.detector = snowboydetect.SnowboyDetect(
            resource_filename=resource.encode(), model_str=model_str.encode())
        self.detector.SetAudioGain(audio_gain)
        self.num_hotwords = self.detector.NumHotwords()

        if len(decoder_model) > 1 and len(sensitivity) == 1:
            sensitivity = sensitivity*self.num_hotwords
        if len(sensitivity) != 0:
            assert self.num_hotwords == len(sensitivity), \
                "number of hotwords in decoder_model (%d) and sensitivity " \
                "(%d) does not match" % (self.num_hotwords, len(sensitivity))
        sensitivity_str = ",".join([str(t) for t in sensitivity])
        if len(sensitivity) != 0:
            self.detector.SetSensitivity(sensitivity_str.encode())

        # create detector buffer
        self.detector_buffer = DetectorRingBuffer(
            self.detector.NumChannels() * self.detector.SampleRate() * 5)
        self.backward_buffer = None

        # connect to the PyAudio stream
        self.audio = pyaudio.PyAudio()
        self.stream_in = self.audio.open(
            input=True, output=False,
            format=self.audio.get_format_from_width(
                self.detector.BitsPerSample() / 8),
            channels=self.detector.NumChannels(),
            rate=self.detector.SampleRate(),
            frames_per_buffer=2048,
            stream_callback=self._audio_callback)

        # listen to interrupots
        signal.signal(signal.SIGINT, self.stop)

        self._enable_continue_recording = continue_recording
        self._output_dir = output_dir
        self._delete_active_recording = delete_active_recording

        Log.debug(self._tag, "AudioHandler created")

    def start(self,
        record_before,
        record_after,
        sleep_time, 
        start_recording_callback=None,
        continue_recording_callback=None,
        stop_recording_callback=None):
        """
        Start hotwor detection. For every `sleep_time` second it checks the
        audio buffer for triggering keywords. Every loop it checks if the loop 
        has been interrupted and breaks if it has. Recording is triggered when 
        the hotword is detected.

        :param Int record_before: seconds to record before hotword.
        :param Int record_after: seconds to record after hotword.
        :param Float sleep_time: how much time in second every loop waits.
        :param Function start_recording_callback: callback function for when a
                                hotword is detected and recording is commenced.
        :param Function continue_recording_callback: callback function for when 
                                a hotword is detected and recording should 
                                continue.
        :param Function stop_recording_callback: callback function for when 
                                recoridng has commenced for the alloted time 
                                should stop.
        :return: None
        """
        self.is_interrupted = False
        self.is_running = True

        if callable(start_recording_callback):
            self._start_recording_callback = start_recording_callback
        if callable(continue_recording_callback):
            self._continue_recording_callback = continue_recording_callback
        if callable(stop_recording_callback):
            self._stop_recording_callback = stop_recording_callback

        self._bytes_per_sample=self.detector.BitsPerSample() / 8
        self._record_before=record_before
        self._record_after=record_after

        self.backward_buffer=BackwardBuffer(
            num_channels=self.detector.NumChannels(),
            sample_rate=self.detector.SampleRate(),
            bytes_per_sample=self.detector.BitsPerSample() / 8,
            record_for=record_before)

        Log.info(self._tag, "Started listening for hotword...")

        while True:
            if self.is_interrupted:
                Log.debug(self._tag, "Interrupt detected")
                break
            elif self.is_terminated:
                Log.debug(self._tag, "Terminate detected")
                break

            data = self.detector_buffer.get()
            if len(data) == 0:
                time.sleep(sleep_time)
                continue

            ans = self.detector.RunDetection(data)
            if ans == -1:
                Log.critical(self._tag,
                    "Error initialising streams or reading audio data")
            elif ans > 0:
                has_recorder=len(self.instance_recorders) > 0
                is_recording=has_recorder and not self.instance_recorders[-1].capture_stopped()

                if not self._enable_continue_recording and is_recording:
                    Log.error(self._tag, "Continue recording disabled")
                    continue
                elif is_recording:
                    Log.info(self._tag, "Continue recording")

                    try:
                        self._timer.cancel()
                    except AttributeError:
                        pass
                    self.instance_recorders[-1].extend_desired_length(self._record_after)

                    if self._continue_recording_callback <> None:
                        self._continue_recording_callback()
                else:
                    Log.info(self._tag, "Start recording")

                    if self._start_recording_callback <> None:
                        self._start_recording_callback()

                    buf_after=ForwardBuffer(
                        num_channels=self.detector.NumChannels(),
                        sample_rate=self.detector.SampleRate(),
                        bytes_per_sample=self._bytes_per_sample,
                        record_for=self._record_after)

                    self.instance_recorders.append(InstanceRecorder(
                        buf_before=self.backward_buffer,
                        buf_after=buf_after,
                        num_channels=self.detector.NumChannels(),
                        sample_rate=self.detector.SampleRate(),
                        bytes_per_sample=self._bytes_per_sample,
                        dir=self._output_dir,
                        delete_active_recording=self._delete_active_recording))

                    self.instance_recorders[-1].start()

                self._timer = threading.Timer(record_after+ADD_TO_RECORD_AFTER, self._stop_recording)
                self._timer.daemon = True
                self._timer.start()

            time.sleep(1)

        Log.info(self._tag, "Stopped listening for hotword")
        self.stop()

    def interrupt(self):
        """
        Interrupt the hotword detection if it is running, otherwise do nothing.

        :return: None
        """
        Log.debug(self._tag, "Interrupt triggered")
        self.is_interrupted = True
        self.detector_buffer.clear()
        for instance_recorder in self.instance_recorders:
            try:
                instance_recorder.interrupt()
            except AttributeError:
                pass

    def stop(self):
        """
        Temporarily stop detection. Users cannot call start() again to detect.

        :return: None
        """
        if not self.is_running or self.is_terminated:
            return

        Log.debug(self._tag, "Will stop detection")

        # Stop detection
        self.is_interrupted = True
        self.is_running = False

        try:
            self._timer.cancel()
            self._timer = None
        except AttributeError:
            pass

    def terminate(self, terminate=False):
        """
        Terminate the audio system. Cannot be recovered from

        :return: None
        """
        if self.is_running:
            self.stop()

        Log.debug(self._tag, "Will terminate audio stream")

        if self.is_terminated:
            return
        self.is_terminated = True

        # Shutdown the audio streams
        try:
            self.stream_in.stop_stream()
            self.stream_in.close()
        except AttributeError:
            pass
        try:
            self.audio.terminate()
        except AttributeError:
            pass

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Write audio from PyAudio to the buffers"""
        try:
            clean_ups = []
            for i in range(0,len(self.instance_recorders)):
                if self.instance_recorders[i].clean_up:
                    clean_ups.append(i)
                    pass

                self.instance_recorders[i].extend(in_data)

            for clean_up in clean_ups:
                del self.instance_recorders[clean_up]
        except AttributeError:
            pass

        self.detector_buffer.extend(in_data)
        try:
            self.backward_buffer.extend(in_data)
        except AttributeError:
            pass

        play_data = chr(0) * len(in_data)
        return play_data, pyaudio.paContinue

    def _stop_recording(self, index=-1):
        """
        Stop the audio recording to disk, called when the hotword was detected 
        some time ago.

        :param int index: Index of the recorder to stop (last be default) 
        :return: None
        """
        Log.info(self._tag, "Stop Recording")

        self._timer = None

        self.instance_recorders[index].stop_capture()

        if self._stop_recording_callback <> None:
            self._stop_recording_callback()

