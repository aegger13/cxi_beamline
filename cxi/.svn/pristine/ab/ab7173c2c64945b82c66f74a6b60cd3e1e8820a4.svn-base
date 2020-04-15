"""
Module to do expected startup tasks and instantiate anything that we need
before setting up the config.
"""

import sys
import datetime

from pyfiglet import Figlet
from pswww import pypsElog

from blutil import config, estr, errorlogger
from blutil.update_checker import start_update_checker

# Allow exec/empty * import
__all__ = []

hutch = "cxi"

# Print starttime
dtstart = datetime.datetime.now()
print "{0}python start: {1}".format(hutch, dtstart.strftime("%Y%h%d-%H:%M:%S"))
sys.stdout.flush()

# Render title
pf = Figlet(font="speed")
print estr(pf.renderText("{0}python".format(hutch.title())), color=hutch)

# Define base directory early to allow error logging
config.HOME_DIR = "/reg/neh/operator/{0}opr/".format(hutch)
config.BASE_DIR = config.HOME_DIR + "{0}python_files/".format(hutch)

# Start error logging early to catch startup errors
logging_dir = "/reg/g/pcds/pds/{}/logfiles/".format(hutch)
errorlogger.IPythonErrLog(logging_dir + 
    "{1:04}/{2:02}/{3:02}_{0}python_errors.log".format(
    hutch, dtstart.year, dtstart.month, dtstart.day))

# Start update checker early to catch updates during startup
start_update_checker()

# Load Elog early to get expname
try:
    elog = pypsElog.pypsElog()
    config.Elog = elog
    exp = elog.experiment["name"]
except Exception, exc:
    config.Elog = None
    print "Could not access the Elog"
    print exc
    exp = raw_input("Please enter the experiment name: \n")

# Export to config
config.hutch = hutch
config.expname = exp
config.dtstart = dtstart

