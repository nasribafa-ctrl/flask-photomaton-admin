#!/usr/bin/env python3

# Raspberry Pi Python 3 TM1637 quad 7-segment LED display driver examples
from time import sleep
import signal
import sys
import RPi.GPIO as GPIO



COIN_PIN = 16
PRICE = 400 
COINS = PRICE
bWaitForStart = False

def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)
    
def coin_interrupt(channel):
    if coins <= 0:
        bWaitForStart = True
        COINS = PRICE
    
if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    #i = 0
    #while True:
        #input_value = GPIO.input(COIN_PIN)
        #if not input_value:
            #i = i+1
            #print(str(i))
    GPIO.add_event_detect(COIN_PIN, GPIO.FALLING, callback=coin_interrupt)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
