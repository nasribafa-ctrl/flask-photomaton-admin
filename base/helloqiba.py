import serial
ser = serial.Serial() #Create Serial Object
ser.baudrate = 115200 #Set the appropriate BaudRate
ser.timeout = 50 #The maximum timeout that the program waits for a reply. If 0 is used, the pot is blocked until readline returns
ser.port = '/dev/ttyACM0' # Specify the device file descriptor
ser.open() #Open the serial connection
ser.write(b'V\n') #Write the version command "V\n" encoded in Binary
s = ser.readline() # Read the response
print('Version:' + s.decode('ascii')) # Print it on the terminal, note the decoding to ascii.
