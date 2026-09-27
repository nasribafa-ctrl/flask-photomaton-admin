import serial
import sys
import datetime
import time




if len( sys.argv ) > 1 :

 port_name = sys.argv[1]
 #Open serial port 
 
 serialPort = serial.Serial(
  port = port_name, baudrate=115200, bytesize=8, timeout=0.1, stopbits=serial.STOPBITS_ONE
 );
 
 last_time = 0
 current_time = datetime.datetime.now() #get initial date for record file name

 #create initial file
 name_current_file = "REC "
 if(current_time.day < 10):
  name_current_file += "0"
 name_current_file += str(current_time.day)
 name_current_file += "-" 
 if(current_time.month < 10):
  name_current_file += "0"
 name_current_file += str(current_time.month)
 name_current_file += "-"
 name_current_file += str(current_time.year)
 name_current_file += ".txt" 
 f = open(name_current_file, "a")
 
 serialPort.write(bytearray("X,1\n\r",'ascii')) #Start sniffer 
 
 while 1: #main loop
  try:  
   if last_time != current_time: #check date to create new record file if new day close current record file and create new record file
    f.close()
    last_time = current_time
    name_current_file = "REC "
    if(current_time.day < 10):
     name_current_file += "0"
    name_current_file += str(current_time.day)
    name_current_file += "-" 
    if(current_time.month < 10):
     name_current_file += "0"
    name_current_file += str(current_time.month)
    name_current_file += "-"
    name_current_file += str(current_time.year)
    name_current_file += ".txt" 
    f = open(name_current_file, "a")
   
   current_time = datetime.datetime.now() #get updated date 
   line = serialPort.readline() #serial read
  
   if line:  #save data
    f.write(line.decode('utf-8'))
  
   time.sleep(0.1)
   
  except KeyboardInterrupt:
   raise SystemExit  
  
else :
 print("Please, enter valid serial port")
