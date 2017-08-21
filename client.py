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
   'command'      : 'start',
   'instructions' : """
size
4
max_iterations
10
t_0
1.0
k_decay
2e-05
anneal
False
metropolis
True
motifs
[(2,1,1,0,1,1,2)]
num_permute
2
   """,
   'function' : """
def permute(arr_board, inp):
    import random
    # performs num_permute random permutation
    board = list([list(r) for r in arr_board]) # copy by val
    N = len(board)
    for i in range(int(inp['num_permute'])):
        n1x,n1y = random.randint(0,N-1),random.randint(0,N-1)
        n2x,n2y = random.randint(0,N-1),random.randint(0,N-1)
        board[n1y][n1x],board[n2y][n2x] = board[n2y][n2x],board[n1y][n1x]
    return board
   """,
   'homedir' : '/home/ian/programming/python/daemon/homedir',
}
buff.send_protocol_message(json.dumps(msg))
#s.send(b'Hello, world')
data = buff.recv_protocol_message()
#s.close()
print('Received ' + repr(data))
