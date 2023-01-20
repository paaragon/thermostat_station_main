from machine import Pin, unique_id, reset
import config
from wifi import Wifi
from dht11 import DHT11
import time
from lcd import LCD
from button import Button
import ubinascii
from mqtt import MQTT
import sys
import json

"""
PIN_NUMBERS
"""
DHT_PIN = 0
LCD_SDA = 5
LCD_SCL = 4
BTN_1_PIN = 2
BTN_2_PIN = 14
BTN_3_PIN = 12
BTN_4_PIN = 13
RELAY_PIN = 15

"""
COMPONENTS DECLARATION
"""
dht_sensor = DHT11(DHT_PIN)
lcd_display = LCD(LCD_SDA, LCD_SCL)
button_1 = Button(BTN_1_PIN)
button_2 = Button(BTN_2_PIN)
button_3 = Button(BTN_3_PIN)
button_4 = Button(BTN_4_PIN)
relay = Pin(RELAY_PIN, Pin.OUT)

"""
MAIN VARIABLES
"""
sensor_latest_read = time.time()
lcd_display_latest_on = time.time()
setted_temp = 20
mode = "L"
curr_temp = None
curr_hum = None

local_client_id = ubinascii.hexlify(unique_id()).decode()

"""
AUX FUNCTIONS
"""


def print_info_text():
    global curr_temp
    global curr_hum
    global setted_temp
    global mode
    temp = str(curr_temp) if curr_temp is not None else "--"
    hum = str(curr_hum) if curr_hum is not None else "--"
    text = "T: %sC Set: %sC\nH: %s%% Mod: %s" % (
        temp, str(setted_temp), hum, mode)
    lcd_display.print(text)


def evaluate_temp():
    global mqtt_client
    publish_status_topic = config.MQTT_TOPIC_PREFIX + "/status"
    if curr_temp < setted_temp:
        print("heater on")
        relay.value(1)
        mqtt_client.publish(publish_status_topic, "1")
    else:
        print("heater off")
        relay.value(0)
        mqtt_client.publish(publish_status_topic, "0")


def mqtt_set_temp(payload):
    global setted_temp
    global lcd_display
    global lcd_display_latest_on
    try:
        setted_temp = int(payload)
        lcd_display.turn_on()
        lcd_display_latest_on = time.time()
        evaluate_temp()
        print_info_text()
    except Exception as e:
        print(str(e))


def set_temp(read_info):
    global curr_temp
    global curr_hum
    curr_temp = read_info["temp"]
    curr_hum = result["hum"]
    evaluate_temp()
    print_info_text()


def set_mode(m):
    global mode
    global publish_mode_topic
    global lcd_display_latest_on
    mode = m
    mqtt_client.publish(publish_mode_topic, mode)
    evaluate_temp()
    lcd_display.turn_on()
    lcd_display_latest_on = time.time()
    evaluate_temp()
    print_info_text()


def subscription_callback(topic, msg):
    global local_client_id
    global mode
    topic_tokens = topic.decode().split("/")
    if len(topic_tokens) == 0:
        print("Payload error")
        print(topic)
        print(msg)
        return

    operation = topic_tokens[1]
    client_id = None
    if len(topic_tokens) > 2:
        client_id = topic_tokens[2]
    print(operation)
    if operation == "set" and client_id != local_client_id:
        lcd_display.turn_on()
        mqtt_set_temp(msg)
        return
    print((operation, client_id, local_client_id, mode))
    if operation == "read" and client_id is not None and client_id != local_client_id and mode == "R":
        print("set remote temp")
        fixed_quotes = msg.decode().replace("'", "\"")
        read_info = json.loads(fixed_quotes)
        set_temp(read_info)
        return
    if operation == "setmode":
        set_mode(msg.decode())
        return

    print((topic.decode(), msg.decode()))


"""
LOGIC STARTS
"""

lcd_display.turn_on()

"""
INITIALIZING DHT11 SENSOR READ
"""
lcd_display.print("INITIALIZING\nDHT11")
retry = 0
while curr_temp is None and retry < 5:
    result = dht_sensor.read()
    if result["temp"] is not None:
        curr_temp = result["temp"]
        curr_hum = result["hum"]
    else:
        time.sleep(2)
    retry += 1

if curr_temp is None:
    print("Error initializing sensor")
    lcd_display.print("SENSOR ERROR")
    sys.exit(1)

"""
CONNECTING WIFI
"""
lcd_display.print("Connecting\nWIFI...")
wifi = Wifi(config.WIFI_SSID, config.WIFI_PASS)
try:
    wifi.connect()
except Exception as e:
    print(str(e))
    lcd_display.print("WIFI ERROR")
    sys.exit(1)


"""
CONNECTING MQTT SERVER
"""
lcd_display.print("Connecting\nMQTT...")
try:
    publish_read_topic = config.MQTT_TOPIC_PREFIX + \
        "/read/" + local_client_id
    mqtt_client = MQTT(local_client_id, subscription_callback)
    mqtt_client.connect()
    mqtt_client.subscribe(config.MQTT_TOPIC_PREFIX + "/#")
except (Exception, RuntimeError) as e:
    print(str(e))
    lcd_display.print("MQTT ERROR")
    sys.exit(1)

print_info_text()

publish_startup_topic = config.MQTT_TOPIC_PREFIX + \
    "/startup/" + local_client_id
mqtt_client.publish(publish_startup_topic, "Hello world!")
publish_set_topic = config.MQTT_TOPIC_PREFIX + "/set/" + local_client_id
mqtt_client.publish(publish_set_topic, str(setted_temp))
publish_mode_topic = config.MQTT_TOPIC_PREFIX + "/mode"
mqtt_client.publish(publish_mode_topic, mode)
evaluate_temp()
while True:
    try:
        mqtt_client.check_msg()
        # turn off lcd_display
        if time.time() - lcd_display_latest_on > config.LCD_DISPLAY_ON_DURATION_SEC:
            lcd_display.turn_off()

        # read the local sensor
        if time.time() - sensor_latest_read > config.SENSOR_READ_DELAY_SEC:
            sensor_latest_read = time.time()
            result = dht_sensor.read()
            if result["temp"] is not None:
                mqtt_client.publish(publish_read_topic, str(result))
                if mode == "L":
                    set_temp(result)

        # increase setted_temp
        if button_1.state() == "DOWN":
            print("btn_1 down")
            setted_temp += 1
            evaluate_temp()
            lcd_display.turn_on()
            lcd_display_latest_on = time.time()
            print_info_text()
            mqtt_client.publish(publish_set_topic, str(setted_temp))

        # decrease setted_temp
        if button_2.state() == "DOWN":
            setted_temp -= 1
            evaluate_temp()
            lcd_display.turn_on()
            lcd_display_latest_on = time.time()
            print_info_text()
            mqtt_client.publish(publish_set_topic, str(setted_temp))

        # turn on lcd_display
        if button_3.state() == "DOWN":
            lcd_display.turn_on()
            lcd_display_latest_on = time.time()

        # change to remote/local mode
        if button_4.state() == "DOWN":
            if mode == "L":
                mode = "R"
            else:
                mode = "L"
            mqtt_client.publish(publish_mode_topic, mode)
            lcd_display.turn_on()
            lcd_display_latest_on = time.time()
            print_info_text()
    except Exception as e:
        print(str(e))
        reset()
