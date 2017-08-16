import sys, time, os
import socket

class BufferedMessage():
   """
   Setup buffered messaging on socket connection.
   """
   def __init__(self, conn, addr):
      """
      Initialize the buffered message.
      """
      self.conn = conn
      self.addr = addr
      
      self.buff = ""
      self.recvsize = 1024
   
   def __enter__(self):
      """
      Enter overload.
      """
      return self

   def __exit__(self, exc_type, exc_value, traceback):
      """
      Exit.
      """
      print("__exit__ : closing connection")
      self.conn.close()

   def __del__(self):
      """
      Delete.
      """
      print("__del__ : closing connection")
      self.conn.close()

   def close(self):
      """
      Close connection.
      """
      print("close : closing connection")
      self.conn.close()

   def recv_protocol_message(self):
      """
      Recieve a message defined by the protocol.
      """
      msg = ""
      
      if len(self.buff) > 0:
         msg = self.buff
         self.buff = ""

      while True:
         data = self.conn.recv(self.recvsize)
         if not data:
            print("breaking")
            break
         index = data.find('\0')
         if index != -1:
            msg += data[:index]
            self.buff = data[index + 1:]
            break
         else:
            msg += data
         
      return msg

   def send_protocol_message(self, msg):
      """
      Send a protocol message.
      """
      self.conn.send(msg + "\0")
         
      

class BufferedSocket():
   """
   Setup a Unix Domain socket with buffered messaging.
   """
   def __init__(self, sname):
      """
      Initialize a socket.
      """
      self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      self.sname = sname
      
      try:
         os.remove(self.sname)
      except OSError:
         pass
      self.s.bind(sname)
      self.s.listen(1)
   
   def accept(self):
      """
      Accept a connection.
      """
      conn, addr = self.s.accept()
      return BufferedMessage(conn, addr)
