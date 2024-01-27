import paho.mqtt.client as mqtt
import tkinter
import time
import sqlite3
import threading
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import lib.oled.SSD1331 as SSD1331
from config import *  # pylint: disable=unused-wildcard-import
from mfrc522 import MFRC522
import neopixel
import board
import tkinter

#collor const for leds'
RED = (255,0,0)
GREEN = (0,255,0)
YELLOW = (255,255,0)
BLUE = (0,0,255)
WHITE = (0,0,0)
# The terminal ID - can be any string.
terminal_id = "MAIN"
# The broker name or IP address.
broker = "10.108.33.125"
# broker = "127.0.0.1"
# broker = "10.0.0.1"
# The MQTT client.
client = mqtt.Client()
# The main window.
window = tkinter.Tk()
#display screen
disp = SSD1331.SSD1331()
#led
pixels = neopixel.NeoPixel(board.D18, 8, brightness=1.0/32, auto_write=False)
# handle turning off the station
execute = True
def redButtonPressedCallback(channel):
    global execute
    execute = False

#handle unblocking stations/nie uzywane
def greenButtonPressedCallback(channel):
    # connect to database.
    connention = sqlite3.connect("workers.db")
    cursor = connention.cursor()
    # get logs
    cursor.execute("SELECT * FROM workers_log")
    log_data = cursor.fetchall()
    station_list = []
    #get list of all stations
    for log in log_data:
        if log[3] not in station_list:
            station_list.append(log[3])
            call_access_station(log[3], "Unblock")

#buzzer to notify of applying the card
def buzzer(state):
    GPIO.output(buzzerPin, not state)

#function to handle leds'
def led_change(color_code: tuple[int,int,int]):
    pixels = neopixel.NeoPixel(board.D18, 8, brightness=1.0/32, auto_write=False)
    pixels.fill(color_code)
    pixels.show()

#send data after reading card
def call_access_station(terminal_id, allowed):
    client.publish(terminal_id, allowed)

# receive from main station if access is granted and handle it
def process_message(client, userdata, message):
    led_change(WHITE)
    # Decode message.
    message_decoded = (str(message.payload.decode("utf-8"))).split(".")

    # Print message to console.
    if message_decoded[1] != "Online" and message_decoded[1] != "Offline":
        led_change(BLUE)

        # connect to database.
        connention = sqlite3.connect("workers.db")
        cursor = connention.cursor()
        # get list of allowed workers 
        cursor.execute("SELECT * FROM workers_allowed")
        allowed_workers = cursor.fetchall()
        #check if worker is allowed access
        allowed_access = "Denied"
        for worker in allowed_workers:
            worker_id = str(worker)
            if message_decoded[1] == worker_id:
                allowed_access = "Allowed"
            else:
                allowed_access = "Denied"
        #log the event
        cursor.execute("INSERT INTO workers_log VALUES (?,?,?,?)",
                       (message_decoded[0], message_decoded[1], message_decoded[2],allowed_access))
        connention.commit()
        connention.close()
        led_change(WHITE)
        print(time.ctime() + ", " +
              message_decoded[1] + " used the RFID card and was"+allowed_access+"access")#message[time,worker_id,terminal_id]
        #return info about access
        call_access_station(message_decoded[2], allowed_access)
    else:
        print(message_decoded[0] + " : " + message_decoded[1])

def connect_to_broker():
    # Connect to the broker.
    client.connect(broker)
    # Send message about conenction.
    client.on_message = process_message
    # Starts client and subscribe to start listening.
    client.loop_start()
    client.subscribe("worker/name")

def print_log_to_window():
    connention = sqlite3.connect("workers.db")
    cursor = connention.cursor()
    cursor.execute("SELECT * FROM workers_log")
    log_entries = cursor.fetchall()
    labels_log_entry = []
    print_log_window = tkinter.Tk()

    for log_entry in log_entries:
        labels_log_entry.append(tkinter.Label(print_log_window, text=(
            "On %s, %s used the terminal %s, and was %s access." % (log_entry[0], log_entry[1], log_entry[2], log_entry[3]))))

    for label in labels_log_entry:
        label.pack(side="top")

    connention.commit()
    connention.close()

    # Display this window.
    print_log_window.mainloop()


def create_main_window():
    window.geometry("250x100")
    window.title("RECEIVER")
    label = tkinter.Label(window, text="Listening to the MQTT")
    exit_button = tkinter.Button(window, text="Stop", command=window.quit)
    print_log_button = tkinter.Button(
        window, text="Print log", command=print_log_to_window)
    register_button = tkinter.Button(
        window, text="Register worker card", command=thread_register_card)

    label.pack()
    exit_button.pack(side="right")
    print_log_button.pack(side="right")
    register_button.pack(side="right")

def thread_register_card():
    thread = threading.Thread(target=loop)
    thread.start()

def loop():
    led_change(YELLOW)

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
                
                register_card(uid)
                #handle registration of card

def register_card(worker):
    led_change(GREEN)
    buzzer(True)
    string_list = map(str, worker)
    result_string = "".join(string_list)
    connention = sqlite3.connect("workers.db")
    cursor = connention.cursor()
    cursor.execute("INSERT INTO workers_allowed VALUES (?)",
                       (result_string,))
    connention.commit()
    connention.close()
    time.sleep(0.5)
    buzzer(False)
    led_change(WHITE)


def disconnect_from_broker():
    # Disconnect the client.
    client.loop_stop()
    client.disconnect()

def run_sender():
    GPIO.add_event_detect(buttonRed, GPIO.FALLING, callback=redButtonPressedCallback, bouncetime=200)
    #GPIO.add_event_detect(buttonGreen, GPIO.FALLING, callback=greenButtonPressedCallback, bouncetime=200)
    #disp.Init()
    #disp.clear()
    connect_to_broker()

    create_main_window()
    # Start to display window (It will stay here until window is displayed)
    window.mainloop()

    disconnect_from_broker()
    #disp.clear()
    #disp.reset()
    GPIO.cleanup()


if __name__ == "__main__":
    run_sender()