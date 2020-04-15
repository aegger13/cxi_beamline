"""
Module that checks if hutch python has been hot-patched since starting the
current session. A background thread will alert the user if modules have been
updated, and suggest that they restart hutch python.
"""

import os
import sys
import time
import threading
import Queue
from IPython.utils import io

update_buffer = Queue.Queue()

def start_update_checker(start_time=None, check_delay=300,
                         msg_repeat_delay=1800, print_now=3600):
    """
    Starts a thread that checks for updates in packages. These messages will
    wait until they have a chance to print at the same time as the out stream.

    start_time: unix timestamp at python start
    check_delay: seconds to wait between checking for updates when none have
                 been found
    msg_repeat_delay: after an update is reported, seconds to wait before
                      reporting again
    print_now: After we fail to print an update message for this many seconds,
               force a (potentially disruptive) report. This should hopefully
               only happen when a terminal is left idle.
    """
    if start_time is None:
        start_time = time.time()
    PythonUpdateBuffer()
    thread = threading.Thread(name="update_checker", target=checker,
                              args=(start_time, check_delay, msg_repeat_delay,
                                    print_now))
    thread.setDaemon(True)
    thread.start()

def checker(start_time, check_delay, msg_repeat_delay, print_now):
    """
    Periodically checks if any package in packages has been updated.
    """
    while True:
        time.sleep(check_delay)
        updated = []
        files = []
        # Check everything that was imported
        for mname, mobj in sys.modules.items():
            if mobj is not None:
                try:
                    fname = mobj.__file__
                except:
                    continue
                if file_ext(fname) == "pyc":
                    fname = fname[:-1]
                fname = os.path.abspath(fname)
                if is_updated(start_time, fname):
                    updated.append(mname)
                    files.append(fname)
        updated.sort()
        # Check for non-python files in same dir as beamline
        beamline = sys.modules.get("beamline")
        if beamline is not None:
            folder = os.path.dirname(beamline.__file__)
            for fname in os.listdir(os.path.abspath(folder)):
                if fname[0] != "." and file_ext(fname) != "pyc":
                    path = os.path.abspath(os.path.join(folder, fname))
                    if is_updated(start_time, path) and path not in files:
                        updated.append(fname)
                        files.append(path)
        if len(updated) > 0:
            txt = "\n================================================="
            txt += "\nThe following packages have been updated:\n\n"
            for pkg in updated:
                txt += "-> {}\n".format(pkg)
            txt += "\nYou may restart python to pick up recent changes."
            txt += "\n=================================================\n"
            update_buffer.put(txt)
            timeout_timer = threading.Timer(print_now, report_update)
            timeout_timer.start()
            update_buffer.join()
            timeout_timer.cancel()
            time.sleep(msg_repeat_delay - check_delay)

def is_updated(start_time, filename):
    """
    Return true if filename has been updated since start_time.
    start_time is a unix timestamp.
    """
    if os.path.exists(filename) and os.path.isfile(filename):
        update_time = os.path.getmtime(filename)
        return update_time > start_time
    else:
        return False

def file_ext(filename):
    """
    Return the file extension of filename.
    """
    return filename.split(".")[-1]

def report_update():
    """
    Print the queued update.
    """
    print get_update()

def get_update():
    """
    Retrieve the queued update.
    """
    val = update_buffer.get()
    update_buffer.task_done()
    return val

def has_update():
    """
    Return True if there is a queued update.
    """
    return not update_buffer.empty()

class PythonUpdateBuffer(io.IOStream):
    """
    Hijack out stream to print our update messages only with other prints.
    """
    def __init__(self):
        self.stream = io.stdout
        io.stdout = self

    def write(self, data):
        """
        Include queued update with the next convenient write.
        """
        if has_update():
            data += get_update()
        self.stream.write(data)

    def flush(self):
        self.stream.flush()

