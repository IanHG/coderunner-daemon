"""
Interface for simulations.


"""

import os
#import signal
import sys
import io
import subprocess
import logging
import time
import threading
import Queue
from models import SimulationSettings,PermuteFunctions
from ast import literal_eval

# Some settings
SINGULARITY_INSTALL_DIR = "/opt/tools/singularity/2.3.1"
SINGULARITY_IMAGE_DIR = "/home/ian/sci2u/master/lan/image"
SIMULATION_LIB_DIR = "/home/ian/sci2u/master/lan/simulation.lib"

# Setup environment
os.environ["PATH"]            = os.environ["PATH"]            + ":" + os.path.join(SINGULARITY_INSTALL_DIR, "bin")
os.environ["LD_LIBRARY_PATH"] = os.path.join(SINGULARITY_INSTALL_DIR, "lib64")
os.environ["LD_RUN_PATH"]     = os.path.join(SINGULARITY_INSTALL_DIR, "lib64")
#prepend_path('PATH',            pathJoin(installDir, 'bin'))
#prepend_path('MANPATH',         pathJoin(installDir, 'share/man'))
#prepend_path('INFOPATH',        pathJoin(installDir, 'share/info'))
#prepend_path('LD_LIBRARY_PATH', pathJoin(installDir, 'lib64'))
#prepend_path('LD_RUN_PATH',     pathJoin(installDir, 'lib64'))
#prepend_path('PKG_CONFIG_PATH', pathJoin(installDir, 'lib/pkgconfig'))

running_simulations = {}

#
#
#
class threadsafe_list():
   """ Implements a thread safe list """

   def __init__(self):
      """ Constructor """
      self._lock = threading.Lock()
      self._list = list()

   def append(self, element):
      """ Append an element """
      self._lock.acquire()
      try:
         self._list.append(element)
      finally:
         self._lock.release()

   def get_last(self):
      """ Get the latest element """
      self._lock.acquire()
      try:
         if len(self._list) > 0:
            return self._list[-1]
         else:
            return None
      finally:
         self._lock.release()


#
#
#
def exec_simulation(args, env = None):
   logging.info("CHILD PROCESS IN EXEC")
   logging.info("CHILD RUNNING ", os.getpid())
   env = env if env else { }
   
   #sys.stdout.write("lol")
   if len(args) >= 1:
      os.execvpe(args[0], args, env)
   else:
      print "Exec error"
   os._exit(0)

#
#
#
def create_input_for_simulation(settings, functionstr):
   inp = "[[INSTRUCTIONS]]\n" + settings + "\n" + "[[INSTRUCTIONSEND]]\n" + "[[FUNCTION]]\n" + functionstr + "\n" + "[[FUNCTIONEND]]"
   return inp

#
#
#
def process_simulation_output(line, outlist):
   regex_iteration = re.compile("(?<=(\[\[ITERATION\]\])).*?(?=\[\[ITERATIONEND\]\])")
   r = regex_iteration.search(line)
   
   if r:
      match = r.group(0) 

      """ We have a match, so we process """
      regex_structure  = re.compile("(?<=(\[\[STRUCTURE\]\])).*?(?=\[\[STRUCTUREEND\]\])")
      regex_statistics = re.compile("(?<=(\[\[STATISTICS\]\])).*?(?=\[\[STATISTICSEND\]\])")
      
      outlist.append({
         "structure"  : regex_structure.search(match).group(0),
         "statistics" : regex_statistics.search(match).group(0),
         })

      """ Remove the processed iteration """
      line = regex_iteration.sub('', line, 1)
      line = re.sub("\[\[ITERATION\]\]\[\[ITERATIONEND\]\]", '', line, 1)

   

#
# Thread target function for running containing the running of simulations (Needed because subprocess is bull-shitting!).
#
def run_simulation_thread(homedir, settings, functionstr, signalqueue, outlist):
   """ Thread target function for wrapping the running of subproces in to a thread.
       Mainly this is done, as thread seems nicer to work with than subprocess.
       
       Will run the simulation through a singularity container such that the simulation 
       is also contained with respect to the OS and other users of the server.
       This is done as people are allowed to submit their own function, in principle giving them
       complete freedom to mess with the system. This is an attempt to limit the effect user can
       have on the system.
   """

   logging.info("THREAD STARTED")
   
   """ Setup I/O """
   logging.info("GETTING FILENOS")
   stdin  = sys.stdin.fileno()
   logging.info("GETTING FILENOS 2")
   stdout = sys.stdout.fileno()
   logging.info("GETTING FILENOS DONE")
   logging.info("SETTING UP PIPES")
   parentread, childwrite  = os.pipe()
   childread , parentwrite = os.pipe()
   
   """ Do the forking """
   logging.info("DOING FORK")
   pid = os.fork()
   logging.info("DONE FORK")
   if pid == 0:
      logging.info("CHILD PROCESS")
      """ Child process """
      os.close(parentread)
      os.close(parentwrite)
      logging.info("CHILD PROCESS DUP")
      os.dup2(childread, stdin)
      os.dup2(childwrite, stdout)
      
      logging.info("CHILD PROCESS WHATEVER")
      home = "/home/ian/programming/singularity/python_hello_world"
      user = "dehurtige"
      userhome = os.path.join(home, user)

      logging.info("CHILD PROCESS EXEC")
      args = ("singularity", "run", "-H", homedir, "--containall", os.path.join(SINGULARITY_IMAGE_DIR, "ubuntu.img"))
      exec_simulation(args)
   elif pid > 0:
      logging.info("PARENT PROCESS")
      """ Parent process """
      os.close(childread)
      os.close(childwrite)
      
      # send input to simulation
      #inp = create_input_for_simulation(settings, functionstr)

      #os.write(parentwrite, inp)
      os.close(parentwrite)
      
      # monitor simulation
      #fcntl.fcntl(parentread, fcntl.F_SETFL, os.O_NONBLOCK)
      while True:
         logging.info("PARENT PROCESS RUNNING LOOP")
         ## handle signals from server thread
         #signal = signalqueue.get_nowait()
         #if signal:
         #   if signal == "STOP":
         #      os.kill(pid, signal.SIGKILL)
         #      break
         #   signalqueue.task_done() # must signal to the queue that task is complete (bullshit interface :D)
         
         # process output
         line += os.read(parentread, 1024)
         if line == "":
            logging.info("PARENT BREAKING")
            break
         logging.info("[PARENT]\n" + line + "[PARENT END]\n")
         process_simulation_output(line, outlist)
      
      """ Clean-up parent """
      logging.info("PARENT PROCESS CLEANING UP")
      p, ret = os.waitpid(pid, 0)
      os.close(parentread)
   else:
      """ Parent process if error in fork() """
      logging.info("Fork went wrong")
   
   #logging.info("THREAD CREATED")
   #with open(homedir + "/stdout.txt","wb") as out:
   #   with open(homedir + "/stderr.txt","wb") as err:
   #      p = subprocess.Popen(
   #         ["singularity", "run", "-H", homedir, "--containall", os.path.join(SINGULARITY_IMAGE_DIR, "ubuntu.img")],
   #         stdout=out,
   #         stderr=err
   #         )
   #
   #p.communicate()
   #logging.info("polling process")
   #while p.poll() == None:
   #   time.usleep(200)

   logging.info("THREAD DONE")

#
# Create user home dir
#
def create_user_homedir(token_user):
   """ Create a home directory for new user.
       The home directory will be created under:

          USERS_HOME_DIR + "/" + <username>

   """
   logging.info("Creating homedir for user : " + token_user.username)

   if not os.path.exists(token_user.directory):
      os.makedirs(token_user.directory)

#
# Start a simulation
#
def start_simulation(request, token_user):
   """ Start a simulation.
   """
   logging.info("STARTING PROCESS PYTHON VERSION IS : \n" + sys.version)

   # Start 
   #if request.POST['command'] == 'Start':
   if 'settings' not in request.POST:
      raise ValueError("No settings provided.")
   if 'functionstr' not in request.POST:
      raise ValueError("No function provided.")

   #if token_user.username in running_simulations:
   if token_user.username not in running_simulations or not running_simulations[token_user.username]['simthread'].isAlive():
      logging.info("LOL")
      logging.info("STARTING PROCESS IN HOME : " + token_user.directory)
      logging.info("USING IMAGE              : " + os.path.join(SINGULARITY_IMAGE_DIR, "ubuntu.img"))
      
      if token_user.username not in running_simulations:
         running_simulations[token_user.username] = { }
      
      # Create queue
      l = threadsafe_list()
      q = Queue.Queue()

      # Create thread running job
      logging.info("CREATING THREAD")
      t = threading.Thread(
            target = run_simulation_thread,
            args = (token_user.directory, request.POST['settings'], request.POST['functionstr'], q, l)   # needs at least one comma... sigh...
            )
      #t.daemon = True
      logging.info("ACTUALLY STARTING THREAD FROM MASTER")
      logging.info("POLLING PROCESS : " + str(t.isAlive()))
      t.start()
      time.sleep(10)
      logging.info("POLLING PROCESS AGAIN : " + str(t.isAlive()))

      #logging.info("Tread is alive : " + str(t.isAlive()))
      
      # Save running simulation so we can poll it later
      logging.info("HERE")
      running_simulations[token_user.username]['simthread'] = t
      running_simulations[token_user.username]['simlist'] = l
      running_simulations[token_user.username]['simqueue'] = q
      logging.info("BUT NOT HERE?")
   else:
      raise ValueError("Simulation already running!")
   #else:
   #   raise ValueError("Command '" + request.POST['command'] + "' not known.")

#
# Stop simulation
#
def stop_simulation(request, token_user):
   """ Stop simulation for user.
   """
   logging.info("Stopping simulation for user.")
   if running_simulations[token_user]['simthread'].isAlive():
      logging.info("Killing simulation")
      #running_simulations[token_user].kill()

#
# Poll a simualtion for its status and results
#
def poll_simulation(token_user):
   """ Will poll a running simulation for its status
       and send back intermediary results.
   """
   logging.info("polling simulation")
   if token_user.username in running_simulations:
      logging.info("POLLING PROCESS : " + str(running_simulations[token_user.username]['simthread'].isAlive()))
      if running_simulations[token_user.username]['simthread'].isAlive():
         running = 'true'
      else:
         running = 'false'
      
      last = running_simulations[token_user.username]['simlist'].get_last()
      
      if last:
         return {
            'running' : running,
            'board' : last['structure'],
            'new_diagram' : last['statistics'],
         }

   return {
      'running' : 'false',
   }

#
# Save a function to database
#
def save_function(request, token_user):
   """ Save a function to database if it is owned by reqeusting user.
       If function is not owned by user, it will not be overwritten.
   """
   logging.info("save_function")
   token_functions = PermuteFunctions.objects.filter(uid=request.POST['functionname'])

   if len(token_functions) == 0:
      # no function with name, we just create it
      token_function, just_created = PermuteFunctions.objects.get_or_create(
            owner = token_user.username,
            uid = request.POST['functionname'],
            function = request.POST['functionstr'],
            )
   elif len(token_functions) == 1:
      # already a function with this name, we need to check that user is actually owner before overwriting.
      token_function = token_functions[0]
      if token_function.owner == token_user.username:
         token_function.function = request.POST['functionstr']
         token_function.save()
      else:
         raise ValueError("User '" + token_user.username + "' is not the owner of function '" + request.POST['functionname'] + "'")
   else:
      raise ValueError("More than 1 entry for function '" + request.POST['functionname'] + "'")

#
# Load a function from database
#
def load_function(request, token_user):
   """ Load a function from database and return as string.
       
       @return{string} Will return the function as a string.
   """
   token_functions = PermuteFunctions.objects.filter(uid=request.POST['functionname'])

   if len(token_functions) != 1:
      raise ValueError("No function with name '" + request.POST['functionname'] + "'")

   return token_functions[0].function

#
# Save settings to database
#
def save_settings(request, token_user):
   """ Save settings to database if it is owned by reqeusting user.
       If settings are not owned by user, it will not be overwritten.
   """
   logging.info("save_settings")
   token_settings = SimulationSettings.objects.filter(uid=request.POST['settingsname'])

   if len(token_settings) == 0:
      # no settings with name, we just create it
      token_setting, just_created = SimulationSettings.objects.get_or_create(
            owner = token_user.username,
            uid = request.POST['settingsname'],
            settings = request.POST['settings'],
            )
   elif len(token_settings) == 1:
      # already a settings with this name, we need to check that user is actually owner before overwriting.
      token_setting = token_settings[0]
      if token_setting.owner == token_user.username:
         token_setting.settings = request.POST['settings']
         token_setting.save()
      else:
         raise ValueError("User '" + token_user.username + "' is not the owner of settings '" + request.POST['settingsname'] + "'")
   else:
      raise ValueError("More than 1 entry for settings '" + request.POST['settingsname'] + "'")

#
# Load a settings from database
#
def load_settings(request, token_user):
   """ Load settings from database and return as string.
       
       @return{string} Will return the settings as a string.
   """
   token_settings = SimulationSettings.objects.filter(uid=request.POST['settingsname'])

   if len(token_settings) != 1:
      raise ValueError("No settings with name '" + request.POST['settingsname'] + "'")

   return token_settings[0].settings
