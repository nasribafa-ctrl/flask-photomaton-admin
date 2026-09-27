'''
Python Script to interface MDB-USB as master with cashless reader as slave.
It is advised to run with high permissions.

Accepts following arguments (default):
    -debug or -d   (0)            1=debug mode   0=only essential prints
    -port or -p    (/dev/ttyACM0) chooses serial port for communication 
    -output or -o  (1)            0=supress all output to console.
example (on linux): sudo python3 mdb_dialogV5.py -d 1 -p /dev/ttyACM2 -o 1

Created 6 Sep 2019 by João Costa & João Amaral - QibaConnect LDA
'''

import serial,io
import time
import argparse,sys,os
import os

VEND_TIMEOUT = 10 #SECONDS

# read from serial and block code execution
def readNWait():
    
    global sio

    for i in range(5): #wait for 500 msecs
        
        buf = sio.readline()
        
        if debug:
            print("Read: " + buf + "\n")

        if len(buf)>0:
            break
        else:
            #print("Waiting for serial port...")
            time.sleep(0.1)
         

    return buf

def write2Serial(message):

    sio.write(message + "\n")
    sio.flush()



#parse argument from user input
def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=True)
    parser.add_argument('-debug', dest='debug',type=int,default=False)
    parser.add_argument('-port',dest='port', type=str,default='/dev/ttyACM0')
    parser.add_argument('-output',dest='console_out', type=int,default=1)
    args = parser.parse_args()
    debug=bool(args.debug)

    if not args.console_out:
        sys.stdout = open(os.devnull, "w") #Disable all output
        
    if debug:print('Debug Activated!')

    return args,debug

def closeSerial():

    
    global ser
    ser.close()

# initial serial port configuration
def initserial():
    
    global sio
    global ser

    ser = serial.Serial()
    
    ser.baudrate = 115200
    
    ser.timeout = 1
    
    ser.port = args.port  # choose USB PORT - default=/dev/ttyACM0
    
    ser.open()  # open serial comunication
    
    time.sleep(1)  # wait for serial comunication to be established

    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

    return ser
      # pass the handler

def writeNReadLn(message):

    if debug: 
        print("Sending: "+message)
    
    write2Serial(message)

    buff = readNWait()
    return buff



#Init MDB master and slave (reader device)
def init_devices():

    res = writeNReadLn("D,2")  # start the master device in Direct Vend mode
    if res.find('D,ERR,"cashless master is on"') != -1:
        print("Restarting Cashless...")
        write2Serial("D,0")  # Master Device was already enabled. Restart it
        write2Serial("D,2") 

        
        res = readNWait()

    
    while res.find('d,STATUS,INIT') == -1:  #Wait for cashless reader (slave) to respond
        print('Waiting for STATUS = INIT. Please enable the reader...')
        res = readNWait()
    
    write2Serial("D,READER,1")  # Enable the reader
    while res.find('d,STATUS,IDLE') == -1 :  #Wait for cashless reader (slave) to be IDLE
        print('Waiting for STATUS = IDLE...')
        res = readNWait()
    if debug: print("Slave device is IDLE...")


#detect if cashless device supports direct vend or not. Returns: false if not, response if yes
def detectDirectVend(amount,product):
    res = writeNReadLn("D,REQ,"+amount+","+product)  # Request Vending
    
    if  'd,ERR,"-1"' in res :  #Normal device returns error
    
        return False
    
    elif 'd,STATUS,VEND' in res: #to test with normal MDB as slave,put here len(res)>5
    
        return res
    
    else:
    
        exit('Unknown response by the slave. Exiting...')

#if device dont supports direct vend, call this function
def normalVend(amount, product):
    print('Please insert payment media in the cashless device...')

    req_str="D,REQ,"+amount+","+product+"\n"
    
    res=readNWait()

    if debug:
        print(res)
    
    if res.find('d,STATUS,CREDIT,')!=-1:
        
        cash= res[res.find('d,STATUS,CREDIT,')+16:len(res)-3]
        
        print('Media Detected with '+cash)
        
        if float(cash)>=float(amount):
        
            res = writeNReadLn(req_str)
        
            if res.find('d,STATUS,VEND')!=-1:
        
                endTransaction(amount,product,res)
        
            else:
        
                exit('Bad Response from the reader. Exiting...')

        else:
        
            exit('Payment media has no sufficient funds to purchase the desired product.\nExiting...')
    
    else:
    
        exit('Bad Response from the reader. Exiting...')


#Call this function when waiting for confirmation by the slave device)
def endTransaction(amount,product,response):
    print('Waiting for transaction to be confirmed...')
    # Joao Amaral , this read is actually made in main ,
    # so no need to wait again res=read_and_wait(ser)

    print("readNWait RES:" + response +"\n")

    if response.find('SUCCESS')!=-1 or response.find('d,STATUS,RESULT,1')!=-1 :
        print('Success! Deviced was charged for '+amount+', for product '+product)
        res = writeNReadLn("D,END")
    elif response.find('FAILED')!=-1 or response.find('d,STATUS,RESULT,-1')!=-1:
        print('Transaction Denied by cashless device!')
    else:
        print('Transaction Failed!')
    if debug:
        print('Going back to IDLE state...')
    

#Disable the slave, master and close serial port.
def end_comunication():
    writeNReadLn("D,READER,0")  # Disable the reader (slave)
    writeNReadLn("D,0")  # Disable the host (master)
    closeSerial()
    
def cancelTransaction():

    res = writeNReadLn("D,REQ,-1")
    if debug:
        print("Transaction cancelled:" + res)
# Main
if __name__ == "__main__":
    args,debug=parse_arguments() #parse user input
    print("Initializing serial port: "+args.port)
    ser = initserial()
    if  ser.is_open:
        init_devices()                
        amount,product=input("Enter the amount and the product to dispense, separated by a space and hit enter\n(ex.:1.2 10): ").strip().split() #wait for user input

        direct = detectDirectVend(amount,product)        
        if not direct: #Automatically falls back to D,1 (normal Vend) and proceed
            normalVend(amount,product)  
        else: #Direct Vend detected
            if debug:
                print('Direct Vend detected')
            
            while True:
                res = readNWait()
                print(res)
                if res.find("d,STATUS,RESULT,") != -1:
                    endTransaction(amount,product,res)
                    break
                #elif i == VEND_TIMEOUT:
                #    cancelTransaction()
                else:
                    time.sleep(1)
        end_comunication()    
            

        
        print("Finished...")
    else:
        print("Failed to open Serial port")