import sys
from Queue import Queue
from threading import Thread

class Worker(Thread):
   """
   Thread executing tasks from a given tasks queue
   """
   def __init__(self, tasks):
      Thread.__init__(self)
      self.tasks = tasks
      self.daemon = True
      self.start()

   def run(self):
      print("Thread startet")
      sys.stdout.flush()
      while True:
         print("waiting for task")
         sys.stdout.flush()
         func, args, kargs = self.tasks.get()
         print("got task")
         sys.stdout.flush()
         try:
            func(*args, **kargs)
         except Exception, e:
            print e
         finally:
            self.tasks.task_done()

class ThreadPool:
   """
   Pool of threads consuming tasks from a queue
   """
   def __init__(self, num_threads):
      """
      Initialize thread pool.
      """
      self.tasks = Queue(num_threads)
      self.done = False
      for _ in range(num_threads): Worker(self.tasks)

   def add_task(self, func, *args, **kargs):
      """
      Add a task to the queue
      """
      print("Adding task")
      self.tasks.put((func, args, kargs))

   def wait_completion(self):
      """
      Wait for completion of all the tasks in the queue
      """
      self.tasks.join()
