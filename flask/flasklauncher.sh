#!/usr/bin/env bash
#Launch photo booth python script at startup

cd "$(dirname "$0")"
#sudo rm -rf captures
source activatevenv.sh
flask run --host="0.0.0.0"
#python main.py
