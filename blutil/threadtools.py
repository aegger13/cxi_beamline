"""
Some basic tools for working with the threading and multiprocessing modules.
"""

import threading
import multiprocessing
import multiprocessing.pool
import multiprocessing.dummy
import Queue
from psp.utils import ensure_context

# Confluence says this is in a package somewhere, but I couldn't find it.
class PycaThread(threading.Thread):
    """
    Thread object that attatches pyca context before running to let us use
    threading with functions that get PV values with psp.Pv.
    """
    def run(self):
        ensure_context()
        threading.Thread.run(self)

# Not clear why this works unless you read ThreadPool source code.
class PycaThreadPool(multiprocessing.pool.ThreadPool):
    """
    Thread pool object that attaches pyca context to each created thread.
    """
    class Process(multiprocessing.dummy.Process, PycaThread):
        """
        Replace ThreadPool.Process.run (Thread.run) with PycaThread.run
        """
        def run(self):
            PycaThread.run(self)
 
class PycaProcess(multiprocessing.Process):
    """
    Process object that attaches pyca context before running to let us use
    Multiprocessing with functions that get PV values with psp.Pv.
    """
    def run(self):
        ensure_context()
        multiprocessing.Process.run(self)

class PycaProcessPool(multiprocessing.pool.Pool):
    """
    Process pool object that attaches pyca context to each process.
    """
    Process = PycaProcess

# Utility functions below:
def thread_with_timeout(func, args=(), kwargs={}, timeout=40, err_msg="", ThreadClass=PycaThread):
    """
    Call func(*args, **kwargs) in a background thread with timeout. If the
    function times out before it returns a value, the main thread will move on
    so the interactive user doesn't get stalled forever. These threads do not
    die and may finish their operation later, so care should be taken.
    """
    my_queue = Queue.Queue()
    def my_func(func, args, kwargs, queue):
        value = func(*args, **kwargs)
        queue.put(value)
    thread = ThreadClass(target=my_func, args=(func, args, kwargs, my_queue,))
    thread.start()
    try:
        return my_queue.get(block=True, timeout=timeout)
    except Queue.Empty:
        if err_msg:
          print err_msg
        return None

