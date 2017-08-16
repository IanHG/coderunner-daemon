#!/usr/bin/env python

import sys, time, os, ast
import json
from daemon import Daemon
from bufferedsocket import BufferedSocket
from threadpool import ThreadPool
from forkexec import forkExec

global_upid = 0

def create_upid():
   """
   Create a unique process id.
   """
   global_upid += 1
   return global_upid

def run_task(buff, processes, msg_dict):
   """
   Handle running a task.
   """
   with forkExec(("ls","-lrth")) as handle:
      pid = handle.pid()
      buff.send_protocol_message(str(pid))
      buff.close()

      while True:
         line = handle.stdout(1024)
         if not line:
            break
         print(line)

def start_task(pool, buff, processes, msg_dict):
   """
   Start a task
   """
   pool.add_task(run_task, buff, processes, msg_dict)

def stop_task(pool, buff, processes, msg_dict):
   """
   Stop a task
   """

def poll_task(pool, buff, processes, msg_dict):
   """
   Poll a task
   """

def connection_handler(pool, buff, processes):
   """
   Handle a connection to the daemon asynchronously.
   """
   msg = buff.recv_protocol_message()
   msg_dict = json.loads(msg)
   
   result = {
      'hello' : lambda pool, buff, processes, msg_dict: sys.stdout.write(msg_dict['msg']),
      'start' : start_task,
      'stop'  : stop_task,
      'poll'  : poll_task, 
   }[msg_dict['command']](pool, buff, processes, msg_dict)

class CodeRunnerDaemon(Daemon):
   """
   Daemon for running python code.
   """
   def run(self):
      """
      Overload of daemon run function.
      Will setup a listening socket for listening for requests.
      """
      print("creating socket")
      sys.stdout.flush()
      s = BufferedSocket("/tmp/socketname")
      pool = ThreadPool(5)
      processes = {}
      
      while True:
         #with s.accept() as buff:
         buff = s.accept()
         connection_handler(pool, buff, processes)
         sys.stdout.flush()

if __name__ == "__main__":
   daemon = CodeRunnerDaemon('/tmp/daemon-coderunner.pid', '/dev/null', '/home/ian/programming/python/daemon/std.out', '/home/ian/programming/python/daemon/std.err')
   if len(sys.argv) == 2:
      if 'start' == sys.argv[1]:
         daemon.start()
      elif 'stop' == sys.argv[1]:
      	daemon.stop()
      elif 'restart' == sys.argv[1]:
      	daemon.restart()
      else:
      	print "Unknown command"
      	sys.exit(2)
      sys.exit(0)
   else:
   	print "usage: %s start|stop|restart" % sys.argv[0]
   	sys.exit(2)
   
