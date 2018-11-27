import pyaudio, os, wave  

from log import Log

class BeepHandler:
    _tag = "beep_handler"

    CHUNK=1024

    """
    Handler to play a beep on the recording commencing.

    :param str on_beep_audio_file: File name to play.
    """
    def __init__(self, on_beep_audio_file):
        dir = os.path.dirname(os.path.realpath(__file__))
        self.filename = on_beep_audio_file
        self.filepath = os.path.join(dir, self.filename)
        self._pyaudio = pyaudio.PyAudio()
        Log.debug(self._tag, "BeepHandler created")

    def play(self):
        """
        Play the beep.
        """
        Log.debug(self._tag, "Play a beep")
        f = wave.open(self.filepath,"rb")
        stream = self._pyaudio.open(format = self._pyaudio.get_format_from_width(f.getsampwidth()),
                channels = f.getnchannels(),
                rate = f.getframerate(),
                output = True)

        data = f.readframes(self.CHUNK)
        while data:
            stream.write(data)
            data = f.readframes(self.CHUNK)

        stream.stop_stream()
        stream.close()

    def terminate(self):
        """
        Terminate the beep handler (no beeps can be played after this).
        """
        Log.debug(self._tag, "BeepHandler termianted")
        self._pyaudio.terminate()

