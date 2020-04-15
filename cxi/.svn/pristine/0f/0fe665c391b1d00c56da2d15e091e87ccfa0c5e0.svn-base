"""
Module for loading hutch python.
"""

# Print start time and banner, start error logger, get elog and expname
from startup import *

# Set up config macros
from cxiconfig import *

# Get beamline devices
from beamline import *

# Get current experiment object
from experiments.load import exp_obj as x

# Import other things we want in the global namespace by default
from blutil.config import Elog as elog
import matplotlib.pyplot as plt
import numpy as np

# Report load time, avoid changing namespace
import blutil.config as _
print "{0}python startup took {1:.2f}s".format(
    _.hutch, (_.dtstart.now() - _.dtstart).total_seconds())

