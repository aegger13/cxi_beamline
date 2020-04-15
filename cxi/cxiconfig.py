"""
File for setting up our config.
Many modules check config for parameters set here.
"""

import os
import pwd
import socket

from blutil import config, threadtools, guessAmiProxy, estr

# Allow exec/empty * import
__all__ = []

##############################################################################
#                           Configuration Settings
##############################################################################

os.environ["PYPS_INTERACTIVE"]="TRUE"
hutch = config.hutch
exp = config.expname

# Epics
config.EPICS_BASE_DIR = "/reg/g/pcds/package/epics/3.14/"
config.EPICS_BASE_DEV_DIR = "/reg/g/pcds/package/epics/3.14-dev/"
config.EPICS_SCREENS = config.EPICS_BASE_DIR + "screens/edm/"
config.EPICS_HUTCH_SCREENS = config.EPICS_BASE_DEV_DIR + \
     "screens/edm/{0}/current/".format(hutch)
     
# Experiments:
config.EXPERIMENT_BASE_DIR = config.HOME_DIR + "experiments/"
config.expname = exp

# Motors:
config._motor_preset_path = config.BASE_DIR + "motor_presets/"
config.epicsArch = "/reg/g/pcds/dist/pds/{0}/misc/epicsArch.txt".format(hutch)

# DAQ:
config.host = socket.gethostname()
config.amiproxy = guessAmiProxy()
if config.amiproxy is None:
    print "Finding amiproxy failed. Pyami monitoring features will not work."
    
config.experiment_directory = config.EXPERIMENT_BASE_DIR + exp
config.scandata_directory = config.EXPERIMENT_BASE_DIR + exp + "/scandata/"
config.scandata_mode = "new_files"

# Make missing directories
def opr_mkdir(path, name):
  if not os.path.isdir(path):
    try: 
      os.mkdir(path)
      if pwd.getpwuid(os.getuid()).pw_name != "{0}opr".format(hutch):
        os.chmod(path, 0777)
      print "Created {0} directory {1}".format(name, path)
    except: 
      print "Could not create {0} directory.".format(name)
      
opr_mkdir(config.BASE_DIR, "{0}python_files".format(hutch))
opr_mkdir(config.EXPERIMENT_BASE_DIR, "experiments")
opr_mkdir(config._motor_preset_path, "motor_presets")
opr_mkdir(config.experiment_directory, "experiment")
opr_mkdir(config.scandata_directory, "scan data")

##############################################################################
#                          Module Configuration
##############################################################################

import matplotlib
matplotlib.use("Qt4Agg") # Parameter Manager compatibility. Trust me.
import matplotlib.pyplot as plt
plt.ion() # Interactive update mode

