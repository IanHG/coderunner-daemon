import os, sys, time

def execvpeChild(args, env = None):
   """
   """
   print("CHILD RUNNING ", os.getpid())
   env = env if env else { }
   
   #sys.stdout.write("lol")
   if len(args) >= 1:
      os.execvpe(args[0], args, env)
   else:
      print "Exec error"
   os._exit(0)

class ForkExecHandle:
   """
   Handle forked process.
   """
   def __init__(self, pid, stdin, stdout, stderr):
      """
      Initialize.
      """
      self._pid = pid
      self._stdin = stdin
      self._stdout = stdout
      self._stderr = stderr

   def __enter__(self):
      """
      Enter
      """
      return self

   def __exit__(self, exc_type, exc_value, traceback):
      """
      Exit
      """
      self.wait(0)
      os.close(self._stdin)
      os.close(self._stdout)
      os.close(self._stderr)

   def stdin(self, msg):
      """
      Write to stdin of child.
      """
      os.write(self._stdin, msg)

   def stdout(self, buffsize):
      """
      Read from stdout.
      """
      return os.read(self._stdout, buffsize)
   
   def stderr(self, buffsize):
      """
      Read from stderr.
      """
      return os.read(self._stderr, buffsize)

   def wait(options = 0):
      """
      Wait for child process.
      """
      os.waitpid(_pid, option)

   def close(pipe = "all"):
      """
      Close connections.
      """
      if pipe == "stdin" or pipe == "all":
         os.close(self._stdin)
      if pipe == "stdout" or pipe == "all":
         os.close(self._stdout)
      if pipe == "stderr" or pipe == "all":
         os.close(self._stderr)


def forkExec(args):
   """
   Fork and exec. Returns a ForkExecHandle to interact with child process through the child process stdin and stdout.
   """
   """ Setup I/O """
   stdin  = sys.stdin.fileno()
   stdout = sys.stdout.fileno()
   stderr = sys.stderr.fileno()
   parentreadout, childwriteout = os.pipe()
   parentreaderr, childwriteerr = os.pipe()
   childread , parentwrite = os.pipe()
   
   """ Do the forking """
   pid = os.fork()
   if pid == 0:
      """ Child process """
      os.close(parentreadout)
      os.close(parentreaderr)
      os.close(parentwrite)
      os.dup2(childread, stdin)
      os.dup2(childwriteout, stdout)
      os.dup2(childwriteerr, stderr)
      
      execvpeChild(args)
   elif pid > 0:
      """ Parent process """
      os.close(childread)
      os.close(childwriteout)
      os.close(childwriteerr)
   else:
      """ Parent process if error in fork() """
      print("Fork went wrong")

   """ Return handle """
   return ForkExecHandle(pid, parentwrite, parentreadout, parentreaderr)
