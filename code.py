import os
import time
import board
import socketpool
import wifi
import busio
import re
import microcontroller
import adafruit_veml7700
import adafruit_minimqtt.adafruit_minimqtt as MQTT

#Setup the VEML7700 via i2c
i2c = busio.I2C(board.GP15, board.GP14)
veml7700 = adafruit_veml7700.VEML7700(i2c)

#Function to be called on MQTT connect.
def connected(client, userdata, flags, rc):
     client.subscribe(update_frequency_topic)

#Function to be called when MQTT receives a message.
def message(client, topic, message):
    #If the topic of the message is the update frequency topic, change the update frequency.
    if topic == update_frequency_topic:
        global update_frequency
        print(f"Changing update frequency from {update_frequency} to {message}.")
        message = re.sub(r'[^\d.]', '', message)
        update_frequency = float(message)

#Setup the MQTT Client
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
pool = socketpool.SocketPool(wifi.radio)
topic = os.getenv("MQTT_SENSOR_TOPIC")
update_frequency_topic = os.getenv("MQTT_UPDATE_FREQ_TOPIC")

mqtt_client = MQTT.MQTT(
    broker=os.getenv("MQTT_HOST"),
    port=os.getenv("MQTT_PORT"),
    username=mqtt_username,
    password=mqtt_password,
    socket_pool=pool,
)

mqtt_client.on_connect = connected
mqtt_client.on_message = message

current_value = 0
update_frequency = 30
wifi_connected = False
mqtt_connected = False

#Try to connect to WiFi.
while wifi_connected == False:
    try:
        print("Connecting to wifi.")
        wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
    except:
        print("Connecting to wifi failed. Will try again in 15 seconds.")
        time.sleep(15)
    
    print("Wifi is connected.")
    wifi_connected = wifi.radio.connected

#Try to connect to MQTT broker.
while mqtt_connected == False:
    try:
        mqtt_client.connect()
    except:
        print("MQTT client failed to connected. Will try again in 15 seconds.")
        time.sleep(15)
    
    print("MQTT client is connected")
    mqtt_connected = mqtt_client.is_connected()

#Main Loop
while True:
    #If MQTT is still connected get the current reading and publish it to the sensor topic.
    if mqtt_client.is_connected():
        try:
            mqtt_client.loop(timeout=1)
            current_value = veml7700.lux
            print(f"Sending current reading {current_value}.")
            mqtt_client.publish(topic, current_value)
            print(f"Sleeping for {update_frequency} seconds")
            time.sleep(update_frequency)
        #If an error occurs, reload the lux sensor.
        except Exception as e:
            print("An error occurred. Reloading in 30 seconds.")
            print(e)
            time.sleep(30)
            microcontroller.reset()
    #If MQTT is not connect, reload the lux sensor.
    else:
        print("MQTT client is no longer connected. Reloading in 30 seconds.")
        time.sleep(30)
        microcontroller.reset()
    
