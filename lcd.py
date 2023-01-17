from i2c_lcd import I2cLcd
from machine import Pin, I2C
from i2c_lcd import I2cLcd


class LCD:

    def __init__(self, sda_pin_n, scl_pin_n):
        sdaPIN = Pin(sda_pin_n)
        sclPIN = Pin(scl_pin_n)

        i2c = I2C(sda=sdaPIN, scl=sclPIN, freq=10000)

        devices = i2c.scan()
        if len(devices) == 0:
            print("No i2c device !")
            raise "No i2c device!"

        print('i2c devices found:', len(devices))

        addr = hex(devices[0])
        self.lcd = I2cLcd(i2c, int(addr), 2, 16)
        self.prev_print = None

    def print(self, text):
        if self.prev_print != text:
            print(text)
            self.lcd.clear()
            self.lcd.move_to(0, 0)
            self.lcd.putstr(text)
            self.prev_print = text

    def turn_off(self):
        self.lcd.backlight_off()

    def turn_on(self):
        self.lcd.backlight_on()
 