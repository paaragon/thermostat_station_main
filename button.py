from machine import Pin


class Button:

    def __init__(
            self,
            pin_n):
        self.pin = Pin(pin_n, Pin.IN, Pin.PULL_UP)
        self.down = False
        self.value = None

    def state(self):
        if not self.down and not self.pin.value():
            self.down = True
            return "DOWN"
        elif self.down and self.pin.value():
            self.down = False
            return "UP"
        return "UNKNOWN"