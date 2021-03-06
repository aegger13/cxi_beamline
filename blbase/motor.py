import sys
import time
import datetime
import os
import re
import threading
import Queue
import subprocess
import numbers
import traceback
import numpy
import pylab as pl
import blutil.tools as tl
import pyca
import psp.Pv as Pv
import blutil
from blutil import notice
from blutil import keypress
from blutil.pypslog import logprint
from blutil.epicsarchive_new import EpicsArchive
try: # Not every environment has pmgr access
  from blutil import pmgr_interface
except:
  pass
import motorPresets as mp
from motorutil import tweak_velo, estimatedTimeNeededForMotion

Elog = None
def set_elog(elog_obj):
  global Elog
  Elog = elog_obj

# MSTA fields
RA_DIRECTION =0
RA_DONE      =1
RA_PLUS_LS   =2
RA_HOME      =3
RA_SM        =4
EA_POSITION  =5
EA_SLIP_STALL=6
EA_HOME      =7
RA_EE        =8
RA_PROBLEM   =9
RA_MOVING    =10
GAIN_SUPPORT =11
RA_COMM_ERR  =12
RA_MINUS_LS  =13
RA_HOMED     =14
RA_ERR       =15
RA_ERR_MASK  =0x7f
RA_STALL     =22
RA_TE        =23
RA_POWERUP   =24
RA_NE        =25
RA_BY0       =26
NA           =27
NOT_INIT     =31

# SEQ_SELN commands
CLEAR_POWERUP=36
CLEAR_STALL  =40
CLEAR_ERR    =48

motor_params = {
   'max_hold_current':('HCMX', 'Hold Current Max '),
   'max_run_current': ('RCMX', 'Run Current Max '),
   'encoderlines':    ('EL', 'Encoder Lines (encoder counts/motor turn/4.)'),
   's1':              ('S1', 'Switch 1 (CW) setting'),
   's2':              ('S2', 'Switch 2 (CCW) setting'),
   'acceleration':    ('ACCL', 'acceleration time'),
   'back_accel':      ('BACC', 'backlash acceleration time'),
   'backlash':        ('BDST', 'backlash distance'),
   'back_speed':      ('BVEL', 'backlash speed'),
   'card':            ('CARD', 'Card Number '),
   'dial_high_limit': ('DHLM', 'Dial High Limit '),
   'direction':       ('DIR',  'User Direction '),
   'dial_low_limit':  ('DLLM', 'Dial Low Limit '),
   'settle_time':     ('DLY',  'Readback settle time (s) '),
   'done_moving':     ('DMOV', 'Done moving to value'),
   'dial_readback':   ('DRBV', 'Dial Readback Value'),
   'description':     ('DESC', 'Description'),
   'dial_drive':      ('DVAL', 'Dial Desired Value'),
   'units':           ('EGU',  'Engineering Units '),
   'encoder_enable':  ('EE',   'Encoder Enable '),
   'encoder_step':    ('ERES', 'Encoder Step Size '),
   'freeze_offset':   ('FOFF', 'Offset-Freeze Switch '),
   'move_fraction':   ('FRAC', 'Move Fraction'),
   'hi_severity':     ('HHSV', 'Hihi Severity '),
   'hi_alarm':        ('HIGH', 'High Alarm Limit '),
   'hihi_alarm':      ('HIHI', 'Hihi Alarm Limit '),
   'high_limit':      ('HLM',  'User High Limit  '),
   'high_limit_set':  ('HLS',  'High Limit Switch  '),
   'hold_current':    ('HC',   'Holding Current '),
   'hw_limit':        ('HLSV', 'HW Lim. Violation Svr '),
   'home_forward':    ('HOMF', 'Home Forward  '),
   'home_reverse':    ('HOMR', 'Home Reverse  '),
   'high_op_range':   ('HOPR', 'High Operating Range'),
   'high_severity':   ('HSV',  'High Severity '),
   'integral_gain':   ('ICOF', 'Integral Gain '),
   'jog_accel':       ('JAR',  'Jog Acceleration (EGU/s^2) '),
   'jog_forward':     ('JOGF', 'Jog motor Forward '),
   'jog_reverse':     ('JOGR', 'Jog motor Reverse'),
   'jog_speed':       ('JVEL', 'Jog Velocity '),
   'last_dial_val':   ('LDVL', 'Last Dial Des Val '),
   'low_limit':       ('LLM',  'User Low Limit  '),
   'low_limit_set':   ('LLS',  'At Low Limit Switch'),
   'lo_severity':     ('LLSV', 'Lolo Severity  '),
   'lolo_alarm':      ('LOLO', 'Lolo Alarm Limit  '),
   'low_op_range':    ('LOPR', 'Low Operating Range '),
   'low_alarm':       ('LOW', ' Low Alarm Limit '),
   'last_rel_val':    ('LRLV', 'Last Rel Value  '),
   'last_dial_drive': ('LRVL', 'Last Raw Des Val  '),
   'last_SPMG':       ('LSPG', 'Last SPMG  '),
   'low_severity':    ('LSV',  'Low Severity  '),
   'last_drive':      ('LVAL', 'Last User Des Val'),
   'soft_limit':      ('LVIO', 'Limit violation  '),
   'in_progress':     ('MIP',  'Motion In Progress '),
   'missed':          ('MISS', 'Ran out of retries '),
   'moving':          ('MOVN', 'Motor is moving  '),
   'resolution':      ('MRES', 'Motor Step Size (EGU)'),
   'motor_status':    ('MSTA', 'Motor Status  '),
   'offset':          ('OFF',  'User Offset (EGU) '),
   'output_mode':     ('OMSL', 'Output Mode Select  '),
   'output':          ('OUT',  'Output Specification '),
   'power_up':        ('PU',   'Power Cycled '),
   'prop_gain':       ('PCOF', 'Proportional Gain '),
   'precision':       ('PREC', 'Display Precision '),
   'readback':        ('RBV',  'User Readback Value '),
   'retry_max':       ('RTRY', 'Max retry count    '),
   'retry_count':     ('RCNT', 'Retry count  '),
   'retry_deadband':  ('RDBD', 'Retry Deadband (EGU)'),
   'dial_difference': ('RDIF', 'Difference rval-rrbv '),
   'effective_res':   ('RES',  'Effective resolution EGU' ),
   'raw_encoder_pos': ('REP',  'Raw Encoder Position '),
   'raw_high_limit':  ('RHLS', 'Raw High Limit Switch'),
   'raw_low_limit':   ('RLLS', 'Raw Low Limit Switch'),
   'relative_value':  ('RLV',  'Relative Value    '),
   'raw_motor_pos':   ('RMP',  'Raw Motor Position '),
   'raw_readback':    ('RRBV', 'Raw Readback Value '),
   'readback_res':    ('RRES', 'Readback Step Size (EGU)'),
   'raw_drive':       ('RVAL', 'Raw Desired Value  '),
   'run_current':     ('RC',   'Run Current  '),  
   'dial_speed':      ('RVEL', 'Raw Velocity '),
   's_speed':         ('S',    'Speed (RPS)  '),
   's_back_speed':    ('BS', 'Backlash Speed (RPS)  '),
   's_base_speed':    ('SBAS', 'Base Speed (RPS)'),
   's_max_speed':     ('SMAX', 'Max Velocity (RPS)'),
   'set':             ('SET',  'Set/Use Switch '),
   'stop_go':         ('SPMG', 'Stop/Pause/Move/Go '),
   's_revolutions':   ('SREV', 'Steps per Revolution '),
   'stop':            ('STOP', 'Stop  '),
   't_direction':     ('TDIR', 'Direction of Travel '),
   'tweak_forward':   ('TWF',  'Tweak motor Forward '),
   'tweak_reverse':   ('TWR',  'Tweak motor Reverse '),
   'tweak_val':       ('TWV',  'Tweak Step Size (EGU) '),
   'use_encoder':     ('UEIP', 'Use Encoder If Present'),
   'u_revolutions':   ('UREV', 'EGU per Revolution  '),
   'use_rdbl':        ('URIP', 'Use RDBL Link If Present'),
   'drive':           ('VAL',  'User Desired Value'),
   'base_speed':      ('VBAS', 'Base Velocity (EGU/s)'),
   'slew_speed':      ('VELO', 'Velocity (EGU/s) '),
   'version':         ('VERS', 'Code Version '),
   'max_speed':       ('VMAX', 'Max Velocity (EGU/s) '),
   'max_speed_xps':   ('SVEL', 'Max Velocity (EGU/s) '),
   'use_home':        ('ATHM', 'uses the Home switch'),
   'deriv_gain':      ('DCOF', 'Derivative Gain '),
   'use_torque':      ('CNEN', 'Enable torque control '),
   'device_type':     ('DTYP', 'Device Type'),
   'record_type':     ('RTYP', 'Record Type'),
   'status':          ('STAT', 'Status'),
   'err_sevr':        ('SEVR', 'Error Severity'),
   'reinit':          ('RINI', 'Reinitialize Motor'),
   'seq_seln':        ('SEQ_SELN', 'SEQ_SELN'),
   'spg':             ('SPG', 'Stop, pause, go')
}

class Motor(object):
  """ 
  motor class
  define a new motor as 
  mymot = motor("XPP:SB2:MMS:10",name="mymotname")
 
  Usage example:

  -> ASK POSITION  <-
  mymot.wm();        # returns current user position
  mymot.wm_string(); # returns current user position as string
  mymot.wm_dial();   # returns current dial position
  mymot.wm_raw();    # returns current motor number of steps

  -> MOVE ABSOLUTE (user value) <-
  mymot.move(3);
  mymot.mv(3);           # as above
  mymot.move_silent(3);  # don't write anything to terminal, good for macros
  mymot.update_move(3);  # show changing postion
  mymot.umv(3);          # show changing postion

  -> MOVE RELATIVE (user value) <-
  mymot.move_relative(2);
  mymot.mvr(2);                  # as above
  mymot.update_move_relative(2); # show changing position
  mymot.umvr(2)                  # show changing position

  -> ASK/CHANGE STATUS <-
  mymot.set(4)          # call current position 4 in user coordinates
  mymot.set_dial(4)     # call current dial position 4 leaving the .OFF unaltered
  mymot.ismoving();     # True if moving
  mymot.stop();         # Send a stop command
  mymot.[get/set]_speed # to change or retrieve current speed (in EGU/s)
    
  """
  __name__ = "Motor"

  def __init__(self,pvname, name=None, readbackpv="default", home="low", **deprecated):
    self._pv_cache = {}

    self.pvname = pvname
    self.name = name or self.get_par_silent("description")

    if readbackpv != "default" and isinstance(readbackpv, basestring):
      self._parname_override("readback", readbackpv)

    # Initialize PVs we need in background threads or callbacks
    self._initialize_params([
        "readback",
        "done_moving",
        "motor_status",
        "resolution",
        "retry_deadband",
        "precision",
        "drive",
        "record_type",
        ])

    if mp.ready():
      self.presets = mp.MotorPresets(self)
    try: # Not every environment has pmgr access
      self.pmgr = pmgr_interface.MotorPmgrSinglet(blutil.guessBeamline(), self)
    except:
      pass

    for key in deprecated:
        print "Warning: motor argument {} is deprecated!".format(key)

    # Legacy code... These should go away once we clean up all the way.
    self.__home = home or ""
    self.__statpv = pvname + ".MSTA"

  #############################
  ### Basic Motor Functions ###
  #############################

  def move(self, pos, relative=False, wait=0, update=False,
           check_limits=True, check_start=3, check_end=True,
           check_problems=True, dial=False, elog=False, silent=False):
    """
    Move this motor to pos.

    Options:
    relative        Move relative to this point instead of from zero.
    wait            If nonzero or True, wait. If negative or True, wait
                    indefinitely. If positive, wait with timeout.
                    Ctrl+c during wait to stop.
    update          Wait and print updates of the motor position. Adopt wait
                    timeout if one is given. Ctrl+c to stop.
    check_limits    Prevent moves to or from locations outside of the limits.
                    Return False if we did not move.
    check_start     Return False if motor does not move within this many
                    seconds.
    check_end       Return False if motor does not reach its destination
    check_problems  Check for and print issues after a move ends
    dial            Use the dial axis instead of the user axis.
    elog            Write move result to the elog. Wait even if wait is False.
    silent          Suppress extra (not error related) prints.
    """
    # Check input
    if not self._usable_number(pos):
      errmsg = "Recieved invalid pos {0} for motor {1} (pv {2})... aborting."
      logprint(errmsg.format(pos, self.name, self.pvname), print_screen=True)
      return False

    # Apply relative and dial
    here = self.wm()
    if dial and update:
      dial_offset = self.get_par("offset")
    if relative:
      pos += here
    elif dial:
      pos += dial_offset
    if not self.within_limits(pos, pypslog=True):
      return False

    # Log move intention
    logmsg = "moving {0} (pv {1}) to {2}, previous position: {3}"
    logprint(logmsg.format(self.name, self.pvname, pos, here))
 
    if update and not silent:
      txt = "Initial position: {}"
      if dial:
        print txt.format(self.wm_string_dial()) 
      else:
        print txt.format(self.wm_string())

    # Set up dmov monitor to look for transition 1 -> 0 if applicable
    if check_start:
        self._monitor_move_start(here)

    # The important part
    self._move(pos)
    readback = self.get_pvobj("readback")

    # Check that we started: wait on dmov 1 -> 0 monitor if hasn't happened
    # If dmov is not available, wait for rbv to move outside of mres
    if check_start:
      if self._usable_number(check_start):
        did_start = self._wait_move_start(check_start)
      else:
        did_start = self._wait_move_start()
      if not did_start:
        self.stop()
        logmsg = "motor {0} (pv {1}) failed to start"
        logprint(logmsg.format(self.name, self.pvname), print_screen=True)
        return False

    # Watch for problems
    if check_problems:
      self._add_wait_cb(self.check_stall)

    # We have to wait if elog
    if elog and not (wait or update):
      wait = True

    # We're done if we aren't waiting
    if not (wait or update):
      return True

    # Interpret wait timeout
    wait_timeout = -1
    if wait:
      if self._usable_number(wait):
        wait_timeout = wait

    # Wait/interrupt block
    if wait or update:
      if update:
        if dial:
          display_offset = dial_offset
        else:
          display_offset = 0
        show_pos = self._update_cb(wait_timeout, display_offset)
      else:
        show_pos = lambda e=None: None
      with CallbackContext(readback, show_pos):
        try:
          if wait_timeout <= 0:
            motion_time = self.estimatedTimeForMotion(abs(here-pos))
            if motion_time is None:
              wait_ok = self.wait(60)
            else:
              wait_ok = self.wait(max(motion_time * 2.0, 60))
          else:
            wait_ok = self.wait(timeout=wait_timeout)
        except KeyboardInterrupt:
          print "\rCtrl+c pressed, stopping motor."
          return self._move_cleanup(False, elog, here, pos)
        except Exception: # Handle other exceptions cleanly before raise
          self._move_cleanup(False, elog, here, pos)
          show_pos()
          traceback.print_exc()
          raise
      show_pos()
      if not wait_ok:
        return self._move_cleanup(False, elog, here, pos)

    # Check that we made it
    if check_end and not self.at_pos(pos):
      logmsg = "Motor {0} (pv {1}) reached {2} instead of desired pos {3}"
      logprint(logmsg.format(self.name, self.pvname, self.wm(), pos),
        print_screen=True)
      return self._move_cleanup(False, elog, here, pos)

    # If everything went ok, return True
    return self._move_cleanup(True, elog, here, pos)

  def _move(self, pos):
    """
    Tell the IOC to move this motor to pos
    """
    self.put_par("drive", pos)

  def _usable_number(self, num):
    """
    Return True if this is a number that could be used.
    (e.g. isn't True, False, NaN, complex, or something strange)
    """
    real = isinstance(num, numbers.Real)
    non_nan = not numpy.isnan(num)
    non_bool = not (num is True or num is False)
    return real and non_nan and non_bool

  def _monitor_move_start(self, start_pos):
    """
    Start a callback to check when the motor has started moving
    """
    self._move_started = threading.Event()
    queue = Queue.Queue()

    dmov = self.get_pvobj("done_moving")
    if dmov.isinitialized:
      def cb(e=None):
        if e is None:
          if not dmov.value:
            self._move_started.set()
            dmov.del_monitor_callback(queue.get())
      id = dmov.add_monitor_callback(cb)
    else:
      rbv = self.get_pvobj("readback")
      res = self.get_par("resolution")
      low = start_pos - res
      high = start_pos + res
      def cb(e=None):
        if e is None:
          if not low < rbv.value < high:
            self._move_started.set()
            rbv.del_monitor_callback(queue.get())
      id = rbv.add_monitor_callback(cb)

    queue.put(id)

  def _wait_move_start(self, timeout=None):
    """
    Block the thread until motor starts moving or timeout.
    Requires _monitor_move_start to have been call before issuing _move.
    """
    return self._move_started.wait(timeout)

  def _update_cb(self, timeout, offset=0):
    """
    Create a monitor callback function to send text updates to the screen.
    If the callback has not been successfully terminated by timeout, will stop
    updating at that time.
    """
    if timeout <= 0:
      timeout = float("inf")
    start = time.time()
    is_done = [False]
    def cb(e=None):
      if e is None and not is_done[0]:
        now = time.time()
        if now-start > timeout:
          is_done[0] = True
        blutil.notice("motor position: {1:{0}}".format(self._prec(), self.wm() - offset))
    return cb

  def _move_cleanup(self, ok, elog, start_pos, goal_pos):
    """
    Things to do at the end of a move (if we waited).
    """
    if not ok:
      self.stop()
    if elog:
      self._record_elog_move(start_pos, goal_pos)
    return ok

  def _record_elog_move(self, start, goal):
    """
    Record the end result of a move to the elog.
    """
    if Elog is None:
      print "Warning: Elog in motor module not initialized!"
    else:
      logmsg = "Moved {0} from {1} by {2} to {3} (req {4})."
      end = self.wm()
      Elog.submit(logmsg.format(self.name, start, end-start, end, goal))

  def move_relative(self, delta):
    """
    Move by delta from the current position.
    """
    return self.move(delta, relative=True)

  def update_move(self, pos, silent=False):
    """
    Move to pos, waiting and updating position to the terminal.
    Press ctrl+c to cancel motion.

    Set silent=True to skip all prints other than the text update.
    """
    return self.move(pos, update=True, silent=silent)

  def update_move_relative(self, delta, silent=False):
    """
    Move by delta from the current position, waiting and updating position to
    the terminal. Press ctrl+c to cancel motion.

    Set silent=True to skip all prints other than the text update.
    """
    return self.move(delta, relative=True, update=True, silent=silent)

  def mv_elog(self, pos, update=True):
    """
    Move to pos and write this move to the elog.
    """
    return self.move(pos, update=update, elog=True)

  def mvr_elog(self, delta, update=True):
    """
    Move by delta from the current position and write this move to the elog.
    """
    return self.move(delta, relative=True, update=update, elog=True)

  def move_dial(self, pos):
    """
    Move to a position in dial coordinates.
    """
    return self.move(pos, dial=True)

  def move_silent(self, pos):
    """
    Move to a position, skipping non error-related prints.
    """
    self.move(pos, silent=True)

  def move_raw(self, pos):
    """
    Move to a raw position.
    """
    return self.put_par("raw_drive", pos)

  mv = move
  mvr = move_relative
  umv = update_move
  umvr = update_move_relative

  def mv_ginput(self, ElogQuestion=True):
    print "Select x-position in current plot by mouseclick\n"
    pos = pl.ginput(1)[0][0]
    print "...moving %s to %g" %(self.name, pos)
    self.move(pos)
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s to %g." %(self.name, pos)
        Elog.submit(elogStr)

  def wm(self):
    """
    Return the current position of the motor.
    """
    return self.get_par("readback")

  def wm_update(self):
    """
    Display current motor position. Update until ctrl+c.
    """
    readback = self.get_pvobj("readback")
    show_pos = self._update_cb(0)
    show_pos()
    with CallbackContext(readback, show_pos):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

  def wm_desired_user(self):
    """
    Return the position the user has requested.
    """
    return self.get_par("drive")

  def wm_string(self):
    """
    Return readback position as string with the right number of decimals
    """
    return "{1:{0}}".format(self._prec(), self.wm())

  def _prec(self):
    """
    Return precision formatting string
    """
    prec = int(self.get_par("precision"))
    if prec == 0:
        return "f"
    else:
        return ".{0}f".format(prec)

  def wm_dial(self):
    """
    Return the current position in dial coordinates.
    """
    return self.get_par("dial_readback")

  def wm_desired_dial(self):
    """
    Return the position the user has requested in dial coordinates.
    """
    return self.get_par("dial_drive")

  def wm_string_dial(self):
    """
    Return dial readback position as string with the right number of decimals
    """
    return "{1:{0}}".format(self._prec(), self.wm_dial())

  def wm_offset(self):
    """
    Return the offset between user and dial coordinates.
    """
    return self.get_par("offset")

  def wm_raw(self):
    """
    Return the raw position.
    """
    return self.get_par("raw_drive")

  def stop(self):
    """
    Stop the motor.
    """
    self.put_par("stop",1)

  def ismoving(self):
    """
    Return True if the motor is moving, False otherwise. Requires a done
    moving PV to exist.
    """
    return not self.get_par("done_moving")

  def wait(self, timeout=60, use_pos=False):
    """
    Wait until the motor has finished moving, or until timeout.
    If use_pos is True, we'll wait on the position being correct instead of on
    the done moving PV.
    Returns True if successfully waited, False otherwise.
    """
    dmov = self.get_pvobj("done_moving")
    if not use_pos and dmov.isinitialized:
      return dmov.wait_for_value(1, timeout)
    else:
      monpv = self.get_pvobj("readback")
      goal = self.get_par("drive")
      deadband = self.get_par("retry_deadband")
      min = goal - abs(deadband)
      max = goal + abs(deadband)
      return monpv.wait_for_range(min, max, timeout)

  #####################
  ### PV Utiltities ###
  #####################
  def get_par(self, parname, sep="."):
    """
    Return the value of the PV associated with parname.
    """
    pvobj = self.get_pvobj(parname, sep)
    pvobj.wait_ready(1)
    return pvobj.value

  def put_par(self, parname, value, sep="."):
    """
    Set the PV associated with parname to value.
    """
    pv = self.get_pvname(parname, sep=sep)
    return Pv.put(pv, value)

  def get_pvname(self, parname=None, sep="."):
    """
    Return the pvname associated with parname.
    """
    if parname is None:
      return self.pvname
    return sep.join((self.pvname, motor_params[parname][0]))

  def get_pvobj(self, parname, sep="."):
    """
    Return the cached pv object associated with parname.
    All pvobjs should connect, initialize, and monitor.
    """
    pyca.attach_context()
    try:
        return self._pv_cache[parname]
    except KeyError:
        pvname = self.get_pvname(parname, sep)
        pv = Pv.Pv(pvname, initialize=True, monitor=True)
        self._pv_cache[parname] = pv
        return pv

  def _initialize_params(self, parnames, sep="."):
    """
    Create pv objs for the cache and initialize.
    In __init__, do this for any field that we need in a background thread or
    a callback, otherwise those may fail.
    """
    for name in parnames:
        self.get_pvobj(name, sep)

  def _parname_override(self, parname, pvname):
    """
    For this motor, use parname -> pvname instead of the default.
    """
    self._pv_cache[parname] = Pv.Pv(pvname, initialize=True, monitor=True)

  def get_par_silent(self,parname,sep="."):
    """
    Return the parameter associated with parname.
    Return None instead of raising pyexc.
    """
    try:
      return self.get_par(parname,sep)
    except pyca.pyexc:
      return None

  def wait_par(self,parname,value=None,match_value=True,sep=".",timeout=60):
    """
    Waits for parname to become value, or to become not value if match_value=False.
    If value is left as None, waits for any change.
    Return True after a successful wait, False if it times out.
    """
    pv_obj = self.get_pvobj(parname, sep=sep)
    if value is not None:
      if match_value:
        ok = pv_obj.wait_condition(lambda: pv_obj.value == value, timeout=timeout)
      else:
        ok = pv_obj.wait_condition(lambda: pv_obj.value != value, timeout=timeout)
    else:
      ok = pv_obj.wait_condition(lambda: True, timeout=timeout)
    return ok

  def _add_wait_cb(self, cb, only_once=True):
    """
    Add a callback for a function to run once the motor stops moving.
    cb should take no arguments.
    """
    try:
      obj = self.get_pvobj("done_moving")
    except Exception, exc:
      logprint("Error in wait callback: {}".format(exc))  
      return False
    queue = Queue.Queue()
    def wait_cb(e):
      if e is None and obj.value == 1:
        cb()
        if only_once:
          obj.del_monitor_callback(queue.get())
    id = obj.add_monitor_callback(wait_cb)
    queue.put(id)
    return True

  def _add_pos_cb(self, cb, pos, only_once=True):
    """
    Add a callback for a function to run once we reach pos.
    cb should take no arguments.
    """
    obj = self.get_pvobj("readback")
    queue = Queue.Queue()
    def pos_cb(e):
      if e is None and self.at_pos(pos):
        cb()
        if only_once:
          obj.del_monitor_callback(queue.get())
    id = obj.add_monitor_callback(pos_cb)
    queue.put(id)
    return True

  ##################
  ### Attributes ###
  ##################
  @property
  def mot_type(self):
    """
    Connect to check the rtyp only the first time we need it, because it won't
    change. Do not wait for connect in __init__ in case we don't have the rtyp
    field (old IOC) to keep beamline startup fast.
    """
    if not hasattr(self, "_mot_type"):
        try:
            self._mot_type = self.get_par("record_type")
        except:
            self._mot_type = "old"
    return self._mot_type

  @property
  def deadband(self):
    """
    Return the current value of retry deadband.
    """
    return self.get_par("retry_deadband")

  ###################
  ### Diagnostics ###
  ###################
  def at_pos(self, pos):
    """
    Return True if the motor is within deadband of pos.
    """
    return pos-self.deadband < self.wm() < pos+self.deadband

  def within_limits(self, pos=None, pypslog=False):
    """
    Return True if pos is within limits.
    Print messages and return False otherwise.
    """
    hilim = self.get_hilim()
    lolim = self.get_lowlim()
    if pos is None:
      pos = self.wm()
    pos_ok = lolim < pos < hilim
    msg = "Position {0} outside of limits {1} and {2} for motor {3} (pv {4})"
    if not pos_ok:
      error = msg.format(pos, lolim, hilim, self.name, self.pvname)
      if pypslog:
        logprint(error)
      else:
        print error
    return pos_ok

  def check_stall(self, verbose=True):
    """
    Print warning and return True if stalled.
    """
    if verbose:
      errmsg = "Motor {} has stalled!".format(self.name)
      return self._check_bit(RA_STALL, 1, errmsg)
    else:
      return self._check_bit(RA_STALL, 1)

  def _check_bit(self, bit, mask=1, errmsg=None):
    """
    Return True and print errmsg if bit is 1 in msta.
    Return False if bit is 0 in msta.
    Return None if we can't check MSTA.
    """
    if self.mot_type == "ims":
      if self._msta_bit(bit, mask):
        if errmsg is not None:
          print errmsg
        return True
      return False

  def _msta_bit(self, bit, mask=1):
    """Return True if bit is 1 in msta."""
    msta = self.get_par("motor_status")
    return self._get_bit(msta, bit, mask)

  def _get_bit(self, num, bit, mask=1):
    """Returns the value of desired bit of num."""
    return (int(num) >> bit) & mask

  def _wait_msta_bit(self, bit, goal, mask=1, timeout=60):
    """Wait for the bit to match goal"""
    if self._msta_bit(bit, mask) == goal:
      ok = True
    else:
      pv_obj = self.get_pvobj("motor_status")
      ok = pv_obj.wait_condition(lambda: self._get_bit(pv_obj.value, bit, mask) == goal, timeout=timeout)
    return ok

  def printLog(self):
    str  = "%s,\tpv %s\n" % (self.name,self.pvname)
    letters=['A','B','C','D','E','F','G','H']
    try:
      for letter in letters:
        byte_array = Pv.get("%s.LOG%s"%(self.pvname,letter))
        char_array = [ chr(char_val) for char_val in byte_array if char_val != 0 ]
        str+=''.join(char_array)+'\n'
    except:
      str+='Could not get log messages for motor'
    return str

  ########################
  ### Motor Management ###
  ########################
  def auto_setup(self):
    """
    Run this after plugging in the smart motor.

    Re-initializes (if necessary), clears powerup, stall flag, and error
    (if necessary), and does an autoconfig.
    """
    if self.mot_type == "xps8p":
        return
    if self.get_par("err_sevr") == 3:
      print "Reinitializing motor {}...".format(self.name)
      self.reinit()
      ok = self.wait_par("err_sevr", 3, match_value=False, timeout=20)
      if ok:
        print "Successfully reinitialized {}.".format(self.name)
        time.sleep(0.5)
      else:
        print "Reinitializing {} timed out. Aborting auto_setup.".format(self.name)
        return

    for i in range(3):
      for clear, name in ((self.clear_pu, "powerup"),
                          (self.clear_stall, "stall flag"),
                          (self.clear_error, "error flag")):
        clear(check=True, wait=False)

        ok = []
        for bit, mask in ((RA_POWERUP, 1), (RA_STALL, 1), (RA_ERR, RA_ERR_MASK)):
          ok.append(self._wait_msta_bit(bit, 0, mask, timeout=10))
    if not all(ok):
      print "Issues with clearing flags for {}".format(self.name)

    try: # Not every environment has pmgr access
      self.pmgr.apply_config(dumb_config=self.name)
    except:
      pass
 
  def reinit(self):
    """Reinitialize connection to motor."""
    self.put_par("reinit", 1)

  def clear_pu(self, check=True, wait=False):
    """
    Clear powerup flag.
    check: bool, if True we'll check if we need to do this and skip if not.
    wait: bool, if True we'll wait until the change takes effect.
    """
    try:
        self._clear_flag(CLEAR_POWERUP, RA_POWERUP, 1, check, wait)
    except Exception: # Might be an old IOC, try the old way
        try:
            Pv.put(self.pvname + ":SET_PU", 0)
        except:
            print "Clear_pu failed!"

  def clear_stall(self, check=True, wait=False):
    """
    Clear stall flag.
    check: bool, if True we'll check if we need to do this and skip if not.
    wait: bool, if True we'll wait until the change takes effect.
    """
    self._clear_flag(CLEAR_STALL, RA_STALL, 1, check, wait)

  def clear_error(self, check=True, wait=False):
    """
    Clear error flag.
    check: bool, if True we'll check if we need to do this and skip if not.
    wait: bool, if True we'll wait until the change takes effect.
    """
    self._clear_flag(CLEAR_ERR, RA_ERR, RA_ERR_MASK, check, wait)

  def _clear_flag(self, seq_cmd, msta_bit, msta_mask, check, wait):
    if check and not self._msta_bit(msta_bit, msta_mask):
        return
    self._seq_seln(seq_cmd)
    if wait:
        ok = self._wait_msta_bit(msta_bit, 0, timeout=20)
        return ok

  def _seq_seln(self, n):
    self.put_par("seq_seln", n, sep=":")

  def reset(self):
    subprocess.Popen(["/reg/g/xpp/scripts/iocreboot", self.pvname])
  
  ###################
  ### __Special__ ###
  ###################
  def __call__(self,value=None):
    """ Shortcut for move and get position, for example: m.gonx(4) moves, m.gonx() returns present position"""
    if value is None:
      return self.wm()
    else:
      self.move(value)

  def __repr__(self):
    return self.status()

  def status(self):
    """ return info for the current motor"""
    str  = "%s\n\tpv %s\n" % (self.name,self.pvname)
    str += "\tcurrent position (user,dial): %f,%f\n" % (self.wm(),self.wm_dial())
    str += "\tuser limits      (low,high) : %f,%f\n" % (self.get_lowlim(),self.get_hilim())
    try:
      str += "\tpreset position             : %s" % (self.presets.state())
    except AttributeError:
      pass
    return str

  def __str__(self):
    """ short string representation of motor """
    return "%s @ user %s" % (self.name,self.wm_string())

  ######################
  ### Move Utilities ###
  ######################
  def tweak(self, initial_stepsize=.1, direction=1):
    help_text = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
    help_text += "g = go abs, s = set"
    print "tweaking motor %s (pv=%s)" % (self.name,self.pvname)
    print "start position: %s" % (self.wm_string())
    if abs(direction) != 1:
      raise ValueError("direction needs to be +1 or -1")
    step = float(initial_stepsize)
    oldstep = 0
    k=keypress.KeyPress()
    readback = self.get_pvobj("readback")
    show_pos = self._update_cb(0)
    with CallbackContext(readback, show_pos):
      try:
        while (k.isq() is False):
          if (oldstep != step):
            notice("stepsize: %f" % step)
            sys.stdout.flush()
            oldstep = step
          k.waitkey()
          if ( k.isu() ):
            step = step*2.
          elif ( k.isd() ):
            step = step/2.
          elif ( k.isr() ):
            self.mvr(step*direction)
          elif ( k.isl() ):
            self.mvr(-step*direction)
          elif ( k.iskey("g") ):
            print "enter absolute position (char to abort go to)"
            sys.stdout.flush()
            v=sys.stdin.readline()
            try:
              v = float(v.strip())
              self.mv(v)
            except:
              print "value cannot be converted to float, exit go to mode ..."
              sys.stdout.flush()
          elif ( k.iskey("s") ):
            print "enter new set value (char to abort setting)"
            sys.stdout.flush()
            v=sys.stdin.readline()
            try:
              v = float(v[0:-1])
              self.set(v)
            except:
              print "value cannot be converted to float, exit go to mode ..."
              sys.stdout.flush()
          elif ( k.isq() ):
            break
          else:
            print help_text
        self.stop()
      except KeyboardInterrupt:
        self.stop()
        return
      except Exception:
        self.stop()
        traceback.print_exc()
        raise

  def tweak_velo(self,initial_stepsize=.1):
    tweak_velo(self,initial_stepsize)

  def jogf_start(self):
    if self.get_par("jog_reverse") == 1:
        self.jog_stop()
        self.wait()
    self.put_par("jog_forward",1)

  def jogr_start(self):
    if self.get_par("jog_forward") == 1:
        self.jog_stop()
        self.wait()
    self.put_par("jog_reverse",1)

  def jog_stop(self):
    self.put_par("jog_forward",0)
    self.put_par("jog_reverse",0)

  ################
  ### Settings ###
  ################
  def set_lims(self,*args):
    if len(args)==1:
      print "please input two values for lower and higher limit"
    elif len(args)==2:
      mnval = np.min(args)
      mxval = np.max(args)
      self.put_par("low_limit",mnval)
      self.put_par("high_limit",mxval)
    else:
      print 'Limits input not understood --> no change of limits'

  def set_lims_relative(self,*args):
    ppos = self.wm()
    if len(args)==1:
      relval = np.abs(args[0])
      self.put_par("low_limit",ppos-relval)
      self.put_par("high_limit",ppos+relval)
    elif len(args)==2:
      mnval = np.min(args)
      mxval = np.max(args)
      self.put_par("low_limit",ppos-mnval)
      self.put_par("high_limit",ppos+mxval)
    else:
      print 'Limits imput not understood --> no change of limits'

  def get_lims(self):
    return [self.get_par("low_limit"),self.get_par("high_limit")]

  def get_hilim(self):
    return self.get_par("high_limit")
  def set_hilim(self,value):
    self.put_par("high_limit",value)
  def get_lowlim(self):
    return self.get_par("low_limit")
  def set_lowlim(self,value):
    self.put_par("low_limit",value)
  def get_dial_hilim(self):
    return self.get_par("dial_high_limit")
  def set_dial_hilim(self,value):
    self.put_par("dial_high_limit",value)
  def get_dial_lowlim(self):
    return self.get_par("dial_low_limit")
  def set_dial_lowlim(self,value):
    self.put_par("dial_low_limit",value)

  def get_speed(self):
    """ return the speed (.VELO) in EGU/s """
    return self.get_par("slew_speed")

  def set_speed(self,value):
    """ set the speed (.VELO) in EGU/s """
    if (value>self.get_max_speed()):
      print "asked to set the speed to %f but the max speed is %f\n" % (value,self.get_max_speed())
    else:
      return self.put_par("slew_speed",value)

  def get_max_speed(self):
    """ return the max speed (.VELO) in EGU/s """
    if self.mot_type == 'ims':
      return self.get_par("max_speed")
    elif self.mot_type == 'xps8p':
      return self.get_par("max_speed_xps")
    else:
      return self.get_par("max_speed")

  def set_max_speed(self, value):
    """ set the max speed (.VELO) in EGU/s """
    if self.mot_type == 'ims':
      return self.put_par("max_speed",value)
    elif self.mot_type == 'xps8p':
      print "asked to set the max speed to %f but max speed is read only for %s motors\n" % (value,mot_type)
    else:
      return self.put_par("max_speed",value)

  def __sign(self):
    dir = self.get_par("direction"); # 1 means inverted
    if (dir == 1):
      return -1
    elif (dir == 0):
      return 1
    else:
      return None

  def set_dial(self,value=0,show_previous=True):
    previous_dial = self.wm_dial()
    previous_user = self.wm()
    self.put_par("set",1); # go in set mode
    time.sleep(0.1); # to make sure we are in set mode
    if (self.get_par("set") != 1):
      print "Failed to go in set mode, try again"
      return
    self.put_par("dial_drive",value)
    self.put_par("set",0); # go in use mode
    current_user = self.wm()
    s = "Resetting dial `%s` (PV: %s) from (dial,user) = (%.4g,%.4g) to (%.4g,%.4g)" % (self.name,self.pvname,previous_dial,previous_user,value,current_user)
    logprint(s,print_screen=True)

  def set(self,value=0,show_previous=True):
    # EPICS does user = dial + offset
    # offset = value + self.__sign()*self.wm_dial()
    current_dial = self.wm_dial()
    current_user = self.wm()
    offset = value - self.__sign()*current_dial
    if (show_previous):
      s = "Resetting user `%s` (PV: %s) from (dial,user) = (%.4g,%.4g) to (%.4g,%.4g)" % (self.name,self.pvname,current_dial,current_user,current_dial,value)
      logprint(s,print_screen=True)
      self.put_par("offset",offset)

  ##############
  ### Extras ###
  ##############
  def expert_screen(self):
    """ Opens Epics motor expert screen for resetting motor after e.g. stalling"""
    executable = 'motor-expert-screen'
    #hutch_location = '~' + blutil.guessBeamline() + 'opr/bin/'
    hutch_location = '/reg/g/xpp/scripts/'
    arg = self.pvname
    if os.path.exists(hutch_location + executable):
        os.system(hutch_location + executable + ' ' + arg)
    else:
        os.system(executable + ' ' + arg)

  def archive(self, start=30, end=0, unit="days", plotit=True):
    """
    Extracts epics archive data of motor readback and dial_readback from start
    days back to end days back. These can be also be floats or datetime
    objects.
    """ 
    arch = EpicsArchive()
    pospv = self.get_pvname("readback")
    dialpv = self.get_pvname("dial_readback")
    tpos, xpos = arch.get_points(pospv, start, end, unit, two_lists=True, raw=True)
    tdia, xdia = arch.get_points(dialpv, start, end, unit, two_lists=True, raw=True)
    tpos = [ datetime.datetime.fromtimestamp(i) for i in tpos ]
    tdia = [ datetime.datetime.fromtimestamp(i) for i in tdia ]
    if len(tpos) == 0 and len(tdia) == 0:
      return "no data"
    if plotit:
      figname = "%s (%s) archive" %(self.name,self.pvname)
      tl.nfigure(figname)
      sph1 = pl.subplot(211)
      pl.ylabel(pospv)
      if len(tpos) > 0:
        pl.plot(tpos,xpos,'.k')
        pl.step(tpos,xpos,where='post',color='k')
      sph2 = pl.subplot(212,sharex=sph1)
      pl.ylabel(dialpv)
      if len(tdia) > 0:
        pl.plot_date(tdia,xdia,'.k')
        pl.step(tdia,xdia,where='post',color='k')
    else:
      return [tpos,xpos,tpos,xdia]

  ########################
  ### Legacy Functions ###
  ########################
  def sethome(self,ask=True, restoreOffset=True, hm_user_pos=0.):
    if (ask):
      if ( not (raw_input('Would you like to use the current position as home (DIAL=0)? (y/n)\n') is 'y') ):
        return 0
    old_offset = self.get_par("offset")
    hm_user_pos = self.wm()
    self.set_dial(0)
    if ( restoreOffset):
      # XPP has this, XCS commented it out!
      def_offset = self.getDefOffset()
      if (def_offset != 999.):
        self.put_par("offset",def_offset)
        return (def_offset - old_offset)
      return 0
    self.set(hm_user_pos)
    return 0

  def home(self,ask=True,move_motor_back=True, restoreOffset=False):
    #homing with a ref-mark
    if ( self.__home[0:3] == ("ref")):
      self.homeRef(ask, move_motor_back, restoreOffset)
    else:
      self.homeLim(ask, move_motor_back, restoreOffset)

  def homeRef(self,ask=True,move_motor_back=True, restoreOffset=False):
    isHomepv = Pv.Pv(self.__statpv, initialize=True)
    res = self.get_par('effective_res')
    orig_user_pos = self.wm()
    #needs to be RRBV for new motors, RMP for old ones....
    #orig_hw_steps = self.get_par("raw_motor_pos")
    orig_hw_steps = self.get_par("raw_readback")
    mot_dir = self.__sign()
    mot_status = self.get_par("motor_status")
    homedb = self.get_par('retry_deadband')
    #minimal distance to home from in motor steps
    homedist = 5000
    if (long(mot_status) >> RA_COM_ERR) & 1:
      print "Error state, please check/fix: "
      self.expert_screen()
      return
    #power cycled
    if (long(mot_status) >> RA_POWERUP) & 1:
        print "Motor %s (pv %s) has been power cycled, resetting:" % (self.name,self.pvname)
        self.clear_pu()
        if raw_input('Would you like to continue w/ homing this motor? (y/n)\n') is 'n':
          return
    #MCode not running
    if (long(mot_status) >> RA_BY0) & 1:
      print "MCode is not running, please fix: "
      self.expert_screen()
      return
    #already homed
    if (long(mot_status) >> RA_HOMED) & 1:
      print "we are already home:"
      #now report the current HW pos back  
      hm_user_pos = self.wm()
      #hm_hw_steps = self.get_par('raw_motor_pos')
      hm_hw_steps = self.get_par('raw_readback')
      #in future use deadband or user par for requested homing precision before issueing warning
      off_zero = hm_hw_steps*res
      if (abs(off_zero) > homedb):
        print 'outside of required homing DB(',homedb,'): home at ', off_zero,self.get_par('units'),'(dial)/',hm_hw_steps,' encoder counts'
        doff = self.sethome(restoreOffset, hm_user_pos)
      return
      #check if we need to move off the current position (~1000 HW steps from zero)
    if ( self.__home == ("ref_lowl")):
      self.mv(self.get_lowlim())
    elif ( self.__home == ("ref_highl")):
      self.mv(self.get_hilim())
    elif ( self.__home == ("ref_high")):
      if (orig_hw_steps*mot_dir < homedist):
        self.mv(homedist*res*mot_dir)
        self.wait()
    elif ( self.__home == ("ref_low")):
      if (orig_hw_steps*mot_dir > -homedist):
        self.mv(-homedist*res*mot_dir)
        self.wait()
    else:
      print 'I do not know where to home from, am at ',orig_user_pos,'(',orig_hw_steps,') encoder steps'
      print 'Should I home from here?'
      if ( not (raw_input('Home from here? (y/n)\n') is 'y') ):
        return
    #now home
    if (mot_dir * orig_hw_steps < 0):
      self.put_par("home_forward",1)
    else:
      self.put_par("home_reverse",1)
    #and now wait for the homing flag w/ a timeout.
    isHomepv.wait_condition(lambda : ((isHomepv.value >> RA_HOMED) & 1) == 1, timeout=60)
    #now report the current HW pos back  
    hm_user_pos = self.wm()
    #hm_hw_steps = self.get_par('raw_motor_pos')
    hm_hw_steps = self.get_par('raw_readback')
    #in future use deadband or user par for requested homing precision before issueing warning
    off_zero = hm_hw_steps*res
    if (abs(off_zero) > homedb):
      print 'outside of required homing DB(',homedb,'): home at ', off_zero,self.get_par('units'),'(dial)/',hm_hw_steps,' encoder counts'
      doff = self.sethome(ask,restoreOffset, hm_user_pos)
      if (move_motor_back):
        self.mv(orig_user_pos + doff)
    else:
      print 'found home within ',hm_hw_steps,' encoder steps from expected 0, moving back to',orig_user_pos
      if (move_motor_back):
        self.mv(orig_user_pos)
    return

  def homeLim(self,ask=True,move_motor_back=True,restoreOffset=False):
    """
    Home to the defined limit switch.

    Usage: 
    self.homeLim()
    self.homeLim(ask=True/False, move_motor_back=True/False)

    Purpose: 
    Will home to the limit switch defined as home and set the soft limit a small
    amount away from that. Will optionally set the dial to zero at the limit and
    move the motor back to it's original position. 
    """

    if self.__home not in ('low', 'high'):
      print "No home position defined for motor %s (pv %s); returning." % (self.name,self.pvname)
      return
    if ( not (raw_input('Home using limit switches? [y/n] ') is 'y') ):
      return

    orig_user_pos = self.wm()
    doff          = 0
    isHomepv = Pv.Pv(self.__statpv, initialize=True)
    res = self.get_par('effective_res')
    #needs to be RRBV for noew motors, RMP for old ones....
    #orig_hw_steps = self.get_par("raw_motor_pos")
    orig_hw_steps = self.get_par("raw_readback")
    mot_dir = self.__sign()
    mot_status = self.get_par("motor_status")
    homedb = self.get_par('retry_deadband')
    #minimal distance to home from in motor steps
    homedist = 5000
    if (long(mot_status) >> RA_COMM_ERR & 1):
      print "Error state, please check/fix: "
      self.expert_screen()
      return
      #power cycled
    if (long(mot_status) >> RA_POWERUP & 1):
        print "Motor %s (pv %s) has been power cycled, resetting:" % (self.name,self.pvname)
        self.clear_pu()
        if raw_input('Would you like to continue w/ homing this motor? (y/n)\n') is 'n':
          return
      #MCode not running
    if (long(mot_status) >> RA_BY0 & 1):
      print "MCode is not running, please fix: "
      self.expert_screen()
      return
      #already homed
    if (long(mot_status) >> RA_HOMED & 1):
      print "we are already home:"
        #now report the current HW pos back  
      hm_user_pos = self.wm()
      #hm_hw_steps = self.get_par('raw_motor_pos')
      hm_hw_steps = self.get_par('raw_readback')
        #in future use deadband or user par for requested homing precision before issueing warning
      off_zero = hm_hw_steps*res
      if (abs(off_zero) > homedb):
        print 'outside of required homing DB(',homedb,'): home at ', off_zero,self.get_par('units'),'(dial)/',hm_hw_steps,' encoder counts'
        doff = self.sethome(restoreOffset, hm_user_pos)
      return

    try:
      #check if we need to move off the current position (~1000 HW steps from zero)
      if ( self.__home == ("low")):
        if (orig_hw_steps*mot_dir < homedist):
          self.move_dial(homedist*res*mot_dir)
          self.wait()
      elif ( self.__home == ("high")):
        if (orig_hw_steps*mot_dir >- homedist):
          self.move_dial(-homedist*res*mot_dir)
          self.wait()
      else:
        print 'I do not know where to home from, am at ',orig_user_pos,'(',orig_hw_steps,') encoder steps'
        print 'Should I home from here?'
        if ( not (raw_input('Home from here? (y/n)\n') is 'y') ):
          return
      #now home
      if (self.__home == "high"):
        self.put_par("home_forward",1)
      else:
        self.put_par("home_reverse",1)
      #and now wait for the homing flag w/ a timeout.
      isHomepv.wait_condition(lambda : ((isHomepv.value >> RA_HOMED) & 1) == 1, timeout=60)
      #now report the current HW pos back  
      hm_user_pos = self.wm()
      #hm_hw_steps = self.get_par('raw_motor_pos')
      hm_hw_steps = self.get_par('raw_readback')
      #in future use deadband or user par for requested homing precision before issueing warning
      off_zero = hm_hw_steps*res
      if (abs(off_zero) > homedb):
        print 'outside of required homing DB(',homedb,'): home at ', off_zero,self.get_par('units'),'(dial)/',hm_hw_steps,' encoder counts'
        doff = self.sethome(ask,restoreOffset, hm_user_pos)
      else:
        print 'found home within ',hm_hw_steps,' encoder steps from expected 0, moving back to',orig_user_pos
      return
    finally:
        if (move_motor_back):
          self.mv(orig_user_pos + doff)

  def wait_for_switch(self):
    lim = self.check_limit_switches()[0]
    while (self.check_limit_switches()[0] == "ok"):
      blutil.notice("waiting for limit switch of motor %s (pv %s)" % (self.name,self.pvname))
      time.sleep(0.2)
    return self.check_limit_switches()[0]
           
  def errorStatus(self):
    """ return info for the setup of the current motor"""
    str  = "%s,\tpv %s\n" % (self.name,self.pvname)
    #check the status and print error message, offer to reset
    motMSTA = int(self.get_par('motor_status'))
    haveError = True
    status = int(Pv.get("%s.MSTA"%self.pvname))
    if (status>>RA_BY0)&1:
      str+= 'MCode not running (e.g. after emergency stop)' #write 63 to SEQ_SELN
      resetCode=63
    elif (status>>RA_POWERUP)&1:
      str+= 'Power cycled!' #write 36 to SEQ_SELN
      resetCode=36
    elif (status>>RA_STALL)&1:
      str+= 'Stalled!' #write 40 to SEQ_SELN
      resetCode=40
    elif (status>>RA_ERR)&127:
      str+= 'Other Error' #write 48 to SEQ_SELN
      resetCode=48
      letters=['H','G','F','E','D','C','B','A']
      for letter in letters:
        byte_array = Pv.get("%s.LOG%s"%(self.pvname,letter))
        char_array = [ chr(char_val) for char_val in byte_array if char_val != 0 ]
        thisline=''.join(char_array)
        if (thisline.find('error')):
          print thisline
          break
      if (raw_input('Would you like to see the last 8 log messages? (y/n)\n') is 'y'):
        print self.printLog()
    else:
      haveError = False
      str+='No Error found!'
    if haveError:
      print str
      if (raw_input('Would you like to reset this error? (y/n)\n') is 'y'):
        Pv.put("%s:SEQ_SELN"%self.pvname , resetCode)  
      return 'Error for motor %s(PV: %s) reset.'%(self.pvname, self.name)
    return str

  def setupStatus(self):
    """ return info for the setup of the current motor"""
    str  = "%s,\tpv %s\n" % (self.name,self.pvname)
    #check encoder setup:
    # if EQ, check if encoded, backlash
    # if EE, check if encoded, deadband
    try:
      partNr = Pv.get('%s.PN'%self.pvname)
    except:
      pass
    if Pv.get("%s.SM"%self.pvname)==0:
      str+= 'Stall Mode: Stop on Stall\n'
    else:
      str+= 'Stall Mode: No Stop\n'
    str+='Limits: '
    if Pv.get("%s.S1"%self.pvname)==0:
      str+='\t 1 not set up'
    if Pv.get("%s.S2"%self.pvname)==0:
      str+='\t 2 not set up'
    str+=' \n'

    str+='Motor Speed: %f (%f turns/sec)\n'%(self.get_par('slew_speed'), self.get_par('s_speed'))
    str+='\t accel. from %f in %f sec\n'%(self.get_par('base_speed'), self.get_par('acceleration'))
    sbas = self.get_par('s_base_speed')
    if (Pv.get('%s.BS'%self.pvname)==sbas):
      Pv.put(('%s.BS'%self.pvname),self.get_par('s_speed'))
    if (Pv.get('%s.HS'%self.pvname)==sbas):
      Pv.put(('%s.HS'%self.pvname),sbas*1.01)

    rdbd = self.get_par('retry_deadband')
    enc = self.get_par('encoder')
    if partNr.find('EQ'):
      if enc==0:
        res = self.get_par('resolution')
        str+='Internally Encoded motor running unencoded with step size of %g\n'%res
      else:
        res = self.get_par('encoder_step')
        str+='Internally Encoded motor running encoded with enc. step size of %g\n'%res
      if self.get_par('backlash') == 0.:
        str+='No Backlash\n'
      else:
        str+='Internally encoded motor with backlash correction of %g (%g enc/motor steps, %g turns)\n'%(self.get_par('backlash'),self.get_par('backlash')/res,self.get_par('backlash')/self.get_par('u_revolutions'))
      if rdbd < res*3:
        str+='EPICS retry deadband of %f tighter than 3 encoder/motor steps.\n'%rdbd
      elif rdbd > res*50:
        str+='EPICS retry deadband of %f (%g steps, %g motor turns), will affect wait function'%(rdbd, rdbd/res, rdbd/self.get_par('u_revolutions'))
    elif partNr.find('EE'):
      if enc!=0:
        res = self.get_par('encoder_step')
        str+='Motor using an external encoder with resolution of %g!'%res
        if self.get_par('backlash') != 0.:
          str+='??? closed loop motor with backlash correction???\n'
      else:
        res = self.get_par('resolution')
        str+='Motor running open loop with resolution of %g!'%res
        if self.get_par('backlash') == 0.:
          str+='no backlash correctio!n\n'
        else:
          str+='backlash correction of %g\n'%(self.get_par('backlash')/res)
      if rdbd < res*3:
        str+='EPICS retry deadband tighter than 3 encoder/motor steps.'
      elif rdbd > res*50:
        str+='EPICS retry deadband of %f (%g steps, %g motor turns), will affect wait function'%(rdbd, rdbd/res, rdbd/self.get_par('u_revolutions'))
    
    return str

  def check_limit_switches(self):
    if self.get_par("low_limit_set"):
      return ("low","low limit switch for motor %s (pv %s) activated" % (self.name,self.pvname))
    elif (self.get_par("high_limit_set")):
      return ("high","high limit switch for motor %s (pv %s) activated" % (self.name,self.pvname))
    else:
      return ("ok","")

  def estimatedTimeForMotion(self,deltaS):
    try:
      if self.mot_type == 'xps8p':
        vBase = 0.0
        vFull = self.get_par("slew_speed")
      elif self.mot_type == 'dmx':
        vBase = 0.0
        vFull = self.get_par("base_speed")
      else:
        vBase = self.get_par("base_speed")
        vFull = self.get_par("slew_speed")
      Acc = (vFull-vBase)/self.get_par("acceleration")
      return estimatedTimeNeededForMotion(deltaS,vBase,vFull,Acc)
    except:
      print "Could not estimate move time for motor %s,(%s)"%(self.name,self.pvname)
      return None

# Auxilliary Classes
class CallbackContext(object):
  def __init__(self, pv, callback):
    self.pv = pv
    self.callback = callback
    self.cbid = None

  def __enter__(self):
    self.cbid = self.pv.add_monitor_callback(self.callback)

  def __exit__(self, eType, eValue, eTrace):
    self.pv.del_monitor_callback(self.cbid)

