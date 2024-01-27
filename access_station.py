import paho.mqtt.client as mqtt
import tkinter
import time
import sqlite3
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import lib.oled.SSD1331 as SSD1331
from config import *  # pylint: disable=unused-wildcard-import
from mfrc522 import MFRC522
import neopixel
import board

#collor const for leds'
RED = (255,0,0)
GREEN = (0,255,0)
YELLOW = (255,255,0)
WHITE = (0,0,0)
# The terminal ID - can be any string.
terminal_id = "Station 0A"
# The broker name or IP address.
broker = "10.108.33.125"
# broker = "127.0.0.1"
# broker = "10.0.0.1"
# The MQTT client.
client = mqtt.Client()
#display screen
disp = SSD1331.SSD1331()
#led
pixels = neopixel.NeoPixel(board.D18, 8, brightness=1.0/32, auto_write=False)
# state of the "door lock", fluff
def lock_door(state):
    lock = state
# handle turning off the station
execute = True
def redButtonPressedCallback(channel):
    global execute
    execute = False

#buzzer to notify of applying the card
def buzzer(state):
    GPIO.output(buzzerPin, not state)

def draw_text(message:str):
    image = Image.new("RGB", (disp.width, disp.height), "WHITE")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('./lib/oled/Font.ttf', 18)
    lines = message.split(" ")
    i = 0
    for line in lines[:1]:
        draw.text((8, i), line, font=font, fill="BLACK")
        i = 40
    disp.ShowImage(image,0,0)

#function to handle leds'
def led_change(color_code: tuple[int,int,int]):
    pixels = neopixel.NeoPixel(board.D18, 8, brightness=1.0/32, auto_write=False)
    pixels.fill(color_code)
    pixels.show()

#send data after reading card
def call_main_station(worker_name, read_time):
    string_list = map(str, worker_name)
    result_string = "".join(string_list)
    client.publish("worker/name", read_time + "." + result_string + "." + terminal_id)

# receive from main station if access is granted and handle it
def process_message(client, userdata, message):
    # Decode message.
    message_decoded = (str(message.payload.decode("utf-8"))).split(".")
    
    if message_decoded[0] == "Allowed":
        led_change(GREEN)
        print(time.ctime() + ", Access granted")
        buzzer(True)
        draw_text("Access Granted")
        time.sleep(0.5)
        buzzer(False)
        time.sleep(1)
        led_change(YELLOW)
    elif message_decoded[0] == "Denied":
        print("Access denied")
        led_change(RED)
        buzzer(True)
        draw_text("Access Denied")
        time.sleep(0.5)
        buzzer(False)
        time.sleep(1)
        led_change(YELLOW)
    draw_text("Apply Card")


def connect_to_broker():
    # Connect to the broker.
    client.connect(broker)
    # Send message about conenction.
    client.publish("worker/name", terminal_id + ".Online")
    # Starts client and subscribe to start listening.
    client.on_message = process_message
    client.loop_start()
    client.subscribe(terminal_id)

def loop():
    led_change(YELLOW)
    draw_text("Apply Card")

    MIFAREReader = MFRC522()
    prevStat = 0
    status = 2
    cardApplied = False
    while execute:
        prevStat = status
        (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
        #check if card is still applied after reading it once
        if (prevStat == status):
            cardApplied = False
        if status == MIFAREReader.MI_OK and not cardApplied:
            (status2, uid) = MIFAREReader.MFRC522_Anticoll()
            if status2 == MIFAREReader.MI_OK:
                cardApplied = True
                call_main_station(uid, time.ctime())
                #access is handled in process_message()

def disconnect_from_broker():
    # Disconnect the client.
    client.publish("worker/name", terminal_id + ".Offline")
    client.loop_stop()
    client.disconnect()

def run_sender():
    GPIO.add_event_detect(buttonRed, GPIO.FALLING, callback=redButtonPressedCallback, bouncetime=200)
    disp.Init()
    disp.clear()
    connect_to_broker()

    loop()

    disconnect_from_broker()
    disp.clear()
    disp.reset()
    GPIO.cleanup()


if __name__ == "__main__":
    run_sender()