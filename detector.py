import os, sys, signal, argparse, time
import threading
import RPi.GPIO as GPIO

from led import LED
from log import Log
from audio import AudioHandler

class Detector(object):
    _tag = "detector"

    """Main detector object, based on `snowboydecoder.py` from Snowboy. Snowboy 
    decoder to detect whether a keyword specified by `decoder_model` exists in a 
    microphone input stream.

    :param decoder_model: decoder model file path; stirng or list of strings
    :param int led_running_pin: BCM pin for the running LED
    :param int led_listening_pin: BCM pin for the listening LED
    :param int led_recording_pin: BCM pin for the recording LED
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
        led_running_pin=24,
        led_listening_pin=15,
        led_recording_pin=18,
        sensitivity=[],
        audio_gain=1,
        continue_recording=False,
        output_dir=".",
        delete_active_recording=False):

        self._is_running = False
        self._is_interrupted = False
        self._is_terminated = False

        GPIO.setmode(GPIO.BCM)

        self._led_running = LED(led_running_pin, 0)
        self._led_listening = LED(led_listening_pin, 0)
        self._led_recording = LED(led_recording_pin, 0)

        self._ready=False
        self._startup_anim_thread = threading.Thread(
            target=self._starting_up)
        self._startup_anim_thread.daemon = False
        self._startup_anim_thread.start()

        self.audio_handler = AudioHandler(
            decoder_model=decoder_model,
            sensitivity=sensitivity,
            audio_gain=audio_gain,
            output_dir=output_dir,
            continue_recording=continue_recording,
            delete_active_recording=delete_active_recording)

        signal.signal(signal.SIGINT, self.interrupt)
        Log.debug(self._tag, "Detector created")

    def wait_on_button(self,
            button_pin=27,
            record_before=60,
            record_after=60,
            sleep_time=0.03,
            start_enabled=False):
        """
        Wait for the button press to start hotword detection. Calls `start` 
        when button is pressed.

        :param int button_pin: BCM pin button is on.
        :param int record_before: seconds to record before hotword, set to -1 
                                for default time.
        :param int record_after: seconds to record after hotword, set to -1 
                                for default time.
        :param function interrupt_check: a function that returns True if the 
                                main loop needs to stop.
        :param float sleep_time: how much time in second every loop waits, set 
                                to -1 for default time..
        :param bool start_enabled: if `true`, will simulate button press
                                initially
        :return: None
        """
        GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        self._button_pin=button_pin

        try:
            self._record_before = record_before
            self._record_after = record_after
            self._sleep_time = sleep_time

            Log.info(self._tag, "Wait for button press...")
            GPIO.add_event_detect(
                button_pin,
                GPIO.BOTH,
                callback=self.button_pressed,
                bouncetime=300)
            self._ready_button_press=start_enabled
            self._ready=True

            while True:
                if self._is_interrupted:
                    break

                time.sleep(1)

            Log.info(self._tag, "Finished waiting for button press")
            self.terminate()
        except RuntimeError:
            pass

    def button_pressed(self, pin):
        Log.info(self._tag, "Button pressed")

        if self.audio_handler.is_running and self._audio_thread.isAlive():
            Log.info(self._tag, "Will interrupt AudioHandler")
            self._led_recording.set(False)
            self._led_listening.set(False)
            self.audio_handler.interrupt()
        else:
            self._detector_thread = threading.Thread(
                target=self.start,
                args=(
                self._record_before,
                self._record_after,
                self._sleep_time,
                False))
            self._detector_thread.daemon = False
            self._detector_thread.start()
            Log.debug(self._tag, "New Detector Thread created")
        

    def start(self,
        record_before=60,
        record_after=60,
        sleep_time=0.03,
        terminate_on_stop=True):
        """
        Start hotwor detection. For every `sleep_time` second it checks the
        audio buffer for triggering keywords. Every loop it checks if the loop 
        has been interrupted and breaks if it has. Recording is triggered when 
        the hotword is detected.

        :param Int record_before: seconds to record before hotword
        :param Int record_after: seconds to record after hotword
        :param Function interrupt_check: a function that returns True if the 
                                main loop needs to stop.
        :param Float sleep_time: how much time in second every loop waits.
        :param Boolean terminate_on_stop: True to terminate the detector when 
                                hotword detection stops.
        :return: None
        """
        Log.debug(self._tag, "Detector started")

        if record_before < 0.0:
            raise ValueError("Cannot record less than 0 seconds before hotword!")
        elif record_after < 0.0:
            raise ValueError("Cannot record less than 0 seconds after hotword!")
        elif sleep_time < 0.0:
            raise ValueError("Cannot sleep less than 0 seconds!")

        self._led_listening.set(True)
       
        self._audio_thread = threading.Thread(
            target=self.audio_handler.start,
            args=(record_before,
                record_after,
                sleep_time,
                self._start_recording,
                None,
                self._stop_recording))
        self._audio_thread.daemon = False
        self._audio_thread.start()
        Log.debug(self._tag, "AudioHandler started")

        while True:
            if self._is_interrupted or not self.audio_handler.is_running:
                break
            time.sleep(1)

        self.audio_handler.stop()
        Log.debug(self._tag, "AudioHandler stop requested")

        if terminate_on_stop:
            self.terminate()

    def terminate(self):
        """
        Terminate rest of the hotword detection system. You should call `stop` 
        first.

        :return: None
        """
        if self._is_terminated:
            return
        self._is_terminated = True

        Log.debug(self._tag, "Will terminate Detector")

        Log.debug(self._tag, "Will terminate AudioHandler")
        self.audio_handler.terminate()

        Log.debug(self._tag, "Will clean up GPIO")
        self._led_listening.set(False)
        self._led_recording.set(False)
        GPIO.cleanup();

    def interrupt(self, signal, frame):
        """
        Handle interrupts, if we're detecting, stop that first. If we're not 
        close the system down completely.

        :return: None
        """
        Log.info(self._tag, "Interrupt triggered")

        if self.audio_handler.is_running and self._audio_thread.isAlive():
            Log.debug(self._tag, "Will interrupt AudioHandler")
            self.audio_handler.interrupt()
            self._led_listening.set(False)
            self._led_recording.set(False)
        else:
            Log.debug(self._tag, "Will interrupt Detector")
            self._is_interrupted = True

    def _starting_up(self):
        """
        Flash the LEDs while setting up.

        :return: None
        """
        self._led_running.set(True)
        self._led_listening.set(False)
        self._led_recording.set(False)

        while not self._ready:
            self._led_running.toggle()
            self._led_listening.toggle()
            self._led_recording.toggle()
            time.sleep(0.1)

        self._led_running.set(True)
        self._led_listening.set(True)
        self._led_recording.set(False)

        for i in range(0, 10):
            self._led_running.toggle()
            self._led_listening.toggle()
            self._led_recording.toggle()
            time.sleep(0.1)

        self._led_running.set(True)
        self._led_listening.set(True)
        self._led_recording.set(True)
        time.sleep(1)
        self._led_running.set(True)
        self._led_listening.set(False)
        self._led_recording.set(False)

        if self._ready_button_press:
            self.button_pressed(self._button_pin)

    def _start_recording(self):
        """
        Turn the recording LED on.

        :return: None
        """
        self._led_recording.set(True)

    def _stop_recording(self):
        """
        Turn the recording LED off.

        :return: None
        """
        self._led_recording.set(False)
