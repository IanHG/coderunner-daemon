#!/usr/bin/env python

import sys, time, os, ast
import json
import threading
import datetime
import Queue
from daemon import Daemon
from bufferedsocket import BufferedSocket
#from threadpool import ThreadPool
from forkexec import forkExec

# Some settings
SINGULARITY_INSTALL_DIR = "/opt/tools/singularity/2.3.1"
SINGULARITY_IMAGE_DIR = "/home/ian/sci2u/master/lan/image"
SIMULATION_LIB_DIR = "/home/ian/sci2u/master/lan/simulation.lib"

# 
def append_environ(env, app):
   if env in os.environ:
      os.environ[env] = os.environ[env] + ":" + app
   else:
      os.environ[env] = app

# Setup environment
def setup_environment():
   append_environ("PATH"           , os.path.join(SINGULARITY_INSTALL_DIR, "bin"))
   append_environ("LD_LIBRARY_PATH", os.path.join(SINGULARITY_INSTALL_DIR, "lib"))
   append_environ("LD_RUN_PATH"    , os.path.join(SINGULARITY_INSTALL_DIR, "lib"))
   append_environ("INCLUDE"        , os.path.join(SINGULARITY_INSTALL_DIR, "include"))

global_upid = 0

class threadsafe_value():
   """ Implements a thread safe list """

   def __init__(self):
      """ Constructor """
      self._lock  = threading.Lock()
      self._value = None

   def set(self, value):
      """ Append an element """
      self._lock.acquire()
      try:
         print("SETTING VALUE")
         sys.stdout.flush()
         self._value = value
      finally:
         self._lock.release()

   def get(self):
      """ Get the latest element """
      self._lock.acquire()
      try:
         print("GETTING VALUE")
         sys.stdout.flush()
         return self._value
      finally:
         self._lock.release()

def create_upid():
   """
   Create a unique process id.
   """
   global global_upid
   global_upid += 1
   return global_upid

class Buffered:
   def __init__(self):
      """
      """
      self.buff = ""
      self.recvsize = 2048

   def recv_protocol_message(self, handle):
      """
      Recieve a message defined by the protocol.
      """
      msg = ""
      empty = False

      while True:
         index = self.buff.find("!")
         if index != -1:
            msg = self.buff[:index]
            self.buff = self.buff[index + 1:]
            break

         data = handle.stdout(self.recvsize)
         if not data:
            empty = True
            break

         self.buff += data
         
      return msg, empty


def run_task(msg_dict, output, signalqueue):
   """
   Handle running a task.
   """
   #print(os.environ['PATH'])

   inp = {
      'instructions' : msg_dict['instructions'],
      'function'     : msg_dict['function'],
   }
   
   print("starting Thread")
   print(json.dumps(inp))
   sys.stdout.flush()

   with forkExec(("/opt/tools/singularity/2.3.1/bin/singularity", "run", "-H", str(msg_dict['homedir']), "--containall", os.path.join(SINGULARITY_IMAGE_DIR, "ubuntu.img"))) as handle:
   #with forkExec(("/home/ian/programming/python/daemon/myprog.py",)) as handle:
   #with forkExec(("/opt/tools/singularity/2.3.1/bin/singularity",)) as handle:
   #with forkExec(("singularity",)) as handle:
   #with forkExec(("ls","-lrth")) as handle:
      #print("sending stdin")
      #sys.stdout.flush()
      handle.stdin(json.dumps(inp) + "!")
      handle.close("stdin")
      #print("sent stdin")
      #sys.stdout.flush()
      
      b = Buffered()
      started = False
      while True:
         #print("starting outer loop")
         #sys.stdout.flush()
         try:
            sig = signalqueue.get_nowait()
            if sig:
               signalqueue.task_done() # must signal to the queue that task is complete (bullshit interface :D)
               if sig == "KILL":
                  #print("KILLING CHILD")
                  #sys.stdout.flush()
                  handle.kill()
                  break
         except:
            #print("CAUGHT EXCEPTION")
            pass
         
         """ Recieve message """
         #print("recieving message")
         #sys.stdout.flush()
         mesg, empty = b.recv_protocol_message(handle)
         #if not mesg:
         if empty:
            break
         
         #print("message recieved")
         #print(mesg)
         #time.sleep(1)
         #sys.stdout.flush()
         
         """ Process message """
         if (not started) and (mesg.find("SIMULATION_START") != -1):
            #print("SIMULATION STARTET")
            #sys.stdout.flush()
            started = True
            continue
         
         if (started) and (mesg.find("SIMULATION_FINISHED") != -1):
            #print("SIMULATION FINISHED")
            #sys.stdout.flush()
            started = False
            continue

         if started:
            #print("SIMULATION OUTPUT")
            #print(mesg)
            sys.stdout.flush()
            output.set(mesg)

      print("THREAD ENDING")
      sys.stdout.flush()


def start_task(pool, buff, processes, msg_dict):
   """
   Start a task
   """
   print("starting task")
   upid = create_upid()
   buff.send_protocol_message(str(upid))
   
   output = threadsafe_value()
   signalqueue = Queue.Queue()

   thread = threading.Thread(
      target = run_task,
      args = (msg_dict, output, signalqueue),
      )
   thread.start()

   processes[str(upid)] = {
      'thread' : thread,
      'output' : output,
      'signal' : signalqueue,
      'starttime' : datetime.datetime.now(),
      'endtime' : None,
   }
   
   print("task is started")

def stop_task(pool, buff, processes, msg_dict):
   """
   Stop a task
   """
   upid = str(msg_dict['upid'])
   if upid in processes:
      processes[upid]['signal'].put("KILL")
   else:
      buff.send_protocol_message("NO UPID : " + upid)

def poll_task(pool, buff, processes, msg_dict):
   """
   Poll a task
   """
   upid = msg_dict['upid']
   if upid in processes:
      value = processes[upid]['output'].get()
      if value:
         value = json.loads(value)
         value['running'] = processes[upid]['thread'].isAlive()
         value = json.dumps(value)
         buff.send_protocol_message(value)
      else:
         buff.send_protocol_message("NO OUTPUT")
   else:
      buff.send_protocol_message("NO UPID : " + upid)

def clean_processes(processes):
   """
   Remove all finished processes, which have an end time longer than 1 hour.
   """
   for upid in processes:
      if not processes[upid]['thread'].isAlive():
         if processes[upid]['endtime']:
            end = processes[upid]['endtime']
            now = datetime.datetime.now()
            delta = now - end
            if delta.seconds > 3600:
               del processes[upid]
         else:
            processes[upid]['endtime'] = datetime.datetime.now()

def connection_handler(pool, buff, processes):
   """
   Handle a connection to the daemon asynchronously.
   """
   msg = buff.recv_protocol_message()
   print("Message recieved: \n")
   print(msg)
   sys.stdout.flush()

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
      print("\n\n\n[[STARTING DAEMON]]")
      print("creating socket")
      setup_environment()
      sys.stdout.flush()
      s = BufferedSocket("/tmp/socketname")
      #pool = ThreadPool(5)
      pool = ""
      processes = {}
      
      while True:
         print("Waiting for connection")
         sys.stdout.flush()
         with s.accept() as buff:
            connection_handler(pool, buff, processes)
            print("Connection handled")
            clean_processes(processes)
            print("Clean done")
            sys.stdout.flush()
         print("End of connection loop")
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
   
