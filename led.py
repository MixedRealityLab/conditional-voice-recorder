import RPi.GPIO as GPIO
import time

class LED(object):
    """
    Controls an LED on a given GPIO pin.

    :param Int pin: pin of the LED
    @param Int init_state: initial state (-1: don't change, 0: off, 1: on)
    """
    def __init__(self, pin, init_state=-1):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)

        if init_state == 0:
            self.set(False)
        elif init_state == 1:
            self.set(T)

    def set(self, state=False):
        """
        Set the state of an LED.
        
        :param Boolean state: new state of the LED (True or False)
        :return: None
        """
        GPIO.output(self.pin, GPIO.HIGH if state else GPIO.LOW)

    def get(self):
        """
        Get the state of an LED.
        
        :return: Boolean
        """
        return GPIO.input(self.pin) == GPIO.HIGH

    def toggle(self):
        """
        Toggle the state of an LED.
        
        :return: None
        """
        self.set(state=not self.get())

    def flash(self, on_for=1):
        """
        Flash an LED for `on_for` seconds.
        
        :param Int on_for: time in seconds to keep the LED on for
        :return: None
        """
        self.set(state=True)
        time.sleep(on_for)
        self.set(state=False)
