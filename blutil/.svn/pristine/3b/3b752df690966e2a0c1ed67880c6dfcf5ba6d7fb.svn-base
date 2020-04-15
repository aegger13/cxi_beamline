"""
Module for logging errors in an IPython session.

The IPythonErrLog class replaces and wraps the IPython.utils.io.stdout
object. When things are going well, it simply relays information to
IPython to handle normally. When an exception is thrown, it also saves
information about the error to a configurable log file.

For each exception, this log file has:
1. Which python session (xpppython, xcspython, mecpython, etc.)
2. Which user on which machine
3. Error timestamp
4. Last n inputs to IPython (currently n=5) and corresponding outputs
5. Full traceback

The intention is to guarantee that we have a traceback to look at when
something goes wrong within hutch python. We'll also have some basic
context. When a user or scientist submits a bug report with no detail
(or forgets to let us know) because experiments are really hectic,
this may help us recreate and debug issues. This is a big problem with
any major hutch python redesign.

Sample Usage:

from blutil.errorlogger import IPythonErrLog as errlog 
errlog("some_log_file.txt")
"""

import re
import sys
import datetime
import socket
import os
import pwd

from IPython.utils import io

"""
This lets us access the global namespace.
The only alternative is to pass In and Out to our class, but this is cleaner
and it guarantees we're getting the correct In and Out objects regardless of
which scope our class is instantiated in.
"""
import __main__
In = __main__.In
Out = __main__.Out

context_lines = 5
host = socket.gethostname()
hutch = host.split("-")[0].lower()
user = pwd.getpwuid(os.getuid())[0]


class IPythonErrLog(io.IOStream):
    """
    Class to encapsulate the io.stdout stream and log exceptions.

    .write(date): called every time text needs to be printed to the screen
    .log_error(data): checks if we need to log an error. If so, logs it.

    Other methods are inherited or implemented to comply with the IOStream
    interface.
    """
    def __init__(self, log_file):
        """
        log_file: filename to save logs to
        """
        self.stream = io.stdout
        io.stdout = self
        self.log_file = log_file
        self.prev_error = None

    def write(self, data):
        """Write to stream and log new errors"""
        self.stream.write(data)
        self.log_error(data)

    def log_error(self, data):
        """If an error is new, log it."""
        if hasattr(sys, "last_value") and sys.last_value != self.prev_error:
            txt = "=" * 75 + "\n"
            txt += "{0}python error for {1}@{2} at {3}\n".format(hutch, user, host, datetime.datetime.now())
            for i in range(len(In) - context_lines, len(In)):
                if i > 0:
                    txt += "In [{0}]: {1}\n".format(i, In[i])
                    try:
                        txt += "Out[{0}]: {1}\n".format(i, Out[i])
                    except:
                        pass
            data = remove_estr(data)
            txt += data + "\n"
            try:
                with open(self.log_file, "a") as f:
                    f.write(txt)
                os.chmod(self.log_file, 0o664)
            except:
                pass
            self.prev_error = sys.last_value

    def flush(self):
        self.stream.flush()

estr = re.compile("\x1b\[.{1,4}m")
def remove_estr(text):
    """
    Helper method to "unformat" enhanced strings.

    In IPython these show up as colored, but in text editors they show up
    as lots of junk control characters. We need to strip the junk
    characters out for the log files to be readable.
    """
    while True:
        match = estr.search(text)
        if match == None:
            return text
        text = text.replace(match.group(0), "")

# If this module is called outside of a hutch python context,
# this should provide an error-logged IPython session for testing.
# This module intentionally relies on no other hutch python code.
if __name__ == "__main__":
    IPythonErrLog("errlog.txt")

