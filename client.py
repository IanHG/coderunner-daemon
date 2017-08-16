#!/usr/bin/env python

# Echo client program
import socket
import time
import json

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/tmp/socketname")
msg = {
   'command' : 'start',
}
s.send(json.dumps(msg) + '\0')
#s.send(b'Hello, world')
#data = s.recv(1024)
s.close()
#print('Received ' + repr(data))
