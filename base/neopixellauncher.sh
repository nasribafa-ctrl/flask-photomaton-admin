#!/usr/bin/env bash
#Launch photo booth python script at startup

cd "$(dirname "$0")"
sudo neopixel/bin/python neopixelServer.py
