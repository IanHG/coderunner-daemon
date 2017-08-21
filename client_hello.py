#!/usr/bin/env python

# Echo client program
import socket
import time
import json
from bufferedsocket import BufferedMessage

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/tmp/socketname")
buff = BufferedMessage(s, "")
msg = {
   'command' : 'hello',
   'msg'     : 'HELLO FROM CLIENT',
}
buff.send_protocol_message(json.dumps(msg))
#s.send(b'Hello, world')
data = buff.recv_protocol_message()
s.close()
print('Received ' + repr(data))
