from time  import sleep
from numpy import floor_divide
from functools import wraps
from threading import Event
from psp import Pv
from blutil import guessBeamline, doctools

hutch_dict = dict(
amo=1,
sxr=2,
xpp=3,
xcs=4,
mfx=7,
cxi=5,
mec=6,
)

def not_owner_warning():
  print "WARNING: We are not the sequence owner! We shouldn't be putting to these PVs!"
  print "If this isn't True, please set the sequence owner to yourself and try again."

def if_owner(f):
  @wraps(f)
  def wrapper(self, *args, **kwargs):
    if self.is_sequence_owner():
      return f(self, *args, **kwargs)
    else:
      return not_owner_warning()
  doc = doctools.argspec(f) + "\n"
  try:
    doc += f.__doc__
  except:
    pass
  wrapper.__doc__ = doc
  return wrapper

class EventSequencer(object):
  def __init__(self, local_iocbase, sequence_group):
    self.iocbase = "ECS:SYS0:%d" % (sequence_group)
    self.local_iocbase = local_iocbase
    self.sequence_group = sequence_group
    self.__mode = ["Once","Repeat N Times","Repeat Forever"]
    self.__status = ["Stopped","Waiting","Playing"]
    self.__beamrate="EVNT:SYS0:1:LCLSBEAMRATE"
    self.define_pvnames()
    self.dictRateToSyncMarker = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7, 0:6}

    self.maxEventCount = 2048
    self.__ec = [0] * self.maxEventCount
    self.__bd = [0] * self.maxEventCount
    self.__fd = [0] * self.maxEventCount
    self.__bc = [0] * self.maxEventCount
    self.__ns = 0

    self._init_update_cb()

  def define_pvnames(self):
    ioc = self.iocbase
    self.__pv_beam_owner     = "ECS:SYS0:0:BEAM_OWNER_ID"
    self.__pv_nsteps         = "%s:LEN"          % (ioc)
    self.__pv_playmode       = "%s:PLYMOD"       % (ioc)
    self.__pv_playcount      = "%s:PLYCNT"       % (ioc)
    self.__pv_playcontrol    = "%s:PLYCTL"       % (ioc)
    self.__pv_playstatus     = "%s:PLSTAT"       % (ioc)
    self.__pv_nrepeats_to_do = "%s:REPCNT"       % (ioc)
    self.__pv_total_count    = "%s:TPLCNT"       % (ioc)
    self.__pv_notify         = "%s:SEQ.PROC"     % (ioc)    
    self.__pv_syncmarker     = "%s:SYNCMARKER"   % (ioc) # 0:0.5 1:1 2:5 3:10 4:30 5:60 6:120 7:360
    self.__pv_beamrequest    = "%s:BEAMPULSEREQ" % (ioc) # 0: TimeSlot 1: Beam
    self.__pv_hutch_id       = "%s:HUTCH_ID"     % (ioc)
    self.__pv_EC_array       = "%s:SEQ.A"        % (ioc) # Event Codes
    self.__pv_BD_array       = "%s:SEQ.B"        % (ioc) # Beam Delays
    self.__pv_FD_array       = "%s:SEQ.C"        % (ioc) # Fiducial Delays
    self.__pv_BC_array       = "%s:SEQ.D"        % (ioc) # Burst Counts. -1: forever, -2: stop

  def beamrate(self):
    while True:
      rate = Pv.get(self.__beamrate)
      if rate == 0.5 or int(rate) == rate:
        break
      sleep(0.1)      
    return float(rate)

  def is_beam_owner(self):
    return Pv.get(self.__pv_beam_owner) == Pv.get(self.__pv_hutch_id)

  def is_sequence_owner(self):
    return Pv.get(self.__pv_hutch_id) == hutch_dict[guessBeamline()]

  def _not_owner_warning(self):
    print "WARNING: We are not the sequence owner! We shouldn't be putting to these PVs!"
    print "If this isn't True, please set the sequence owner to yourself and try again."

  @if_owner
  def setSyncMarker(self,rate):
    Pv.put(self.__pv_syncmarker, self.dictRateToSyncMarker[rate])     

  def getSyncMarker(self):
    val = Pv.get(self.__pv_syncmarker)
    return self.dictRateToSyncMarker.keys()[self.dictRateToSyncMarker.values().index(val)]

  @if_owner
  def setnsteps(self,nsteps):
    self.__ns = nsteps
    Pv.put(self.__pv_nsteps,nsteps)  

  def getnsteps(self, internal=False):
    if internal:
      return self.__ns
    else:
      return Pv.get(self.__pv_nsteps)

  def getSettingsInternal(self):
    output = dict(beamcode=[],deltabeam=[],deltafiducial=[],comments=[])
    for n in range(self.getnsteps(internal=True)):
      output['deltabeam'].append(self.__bd[n])
      output['beamcode'].append(self.__ec[n])
      output['deltafiducial'].append(self.__fd[n])
    return output

  def __beamcode_at_step(self,stepn,eventcode):
    self.__ec[stepn] = eventcode

  def __deltabeam_at_step(self,stepn,delta):
    self.__bd[stepn] = delta

  @if_owner
  def __comment_at_step(self,stepn,comment):
    # Example: XXX:ECS:IOC:01:EC_4:00.DESC
    if stepn<20:
      pvname = "%s:EC_%d:%02d.DESC" % (self.local_iocbase,self.sequence_group,stepn)
      Pv.put(pvname,comment)

  def __deltafiducial_at_step(self,stepn,delta=0):
    self.__fd[stepn] = delta

  def __burst_at_step(self,stepn,delta=0):
    self.__bc[stepn] = delta

  def setstep(self, stepn, beamcode, deltabeam, fiducial=0, burst=0, comment="", verbose=False):
    if (verbose):
      print "Setting step #%d to beamcode %d, beam delay %d, fid %d, burst %d" % (stepn,beamcode,deltabeam,fiducial,burst)
    self.__beamcode_at_step     (stepn,beamcode)
    self.__deltabeam_at_step    (stepn,deltabeam)
    self.__deltafiducial_at_step(stepn,fiducial)
    self.__burst_at_step        (stepn,burst)
    if comment != "":
      self.__comment_at_step(stepn,comment)

  def modeOnce(self):
    self.__setmode("Once")

  def modeNtimes(self,N=1):
    self.__setmode("Repeat N Times",N)

  def modeForever(self):
    self.__setmode("Repeat Forever")

  @if_owner
  def __setmode(self,mode,Ntimes=1):
    pvname=self.__pv_playmode
    if (mode == "Once"):
      Pv.put(pvname,0)
    elif (mode == "Repeat N Times"):
      Pv.put(pvname,1)
      Pv.put(self.__pv_nrepeats_to_do,Ntimes)
    elif (mode == "Repeat Forever"):
      Pv.put(pvname,2)
    else:
      print "mode must be Once|Repeat N Tiems|Repeat Forever"
      return

  def __getnpulses_in_play(self):
    return Pv.get(self.__pv_playcount)

  def __getnrepeats_to_do(self):
    return Pv.get(self.__pv_nrepeats_to_do)

  def getmode(self):
    pvname=self.__pv_playmode
    ret=Pv.get(pvname)
    return self.__mode[ret]

  @if_owner
  def start(self):
    self.__total_count = Pv.get(self.__pv_total_count)
    Pv.put(self.__pv_playcontrol,1)

  @if_owner
  def stop(self):
    Pv.put(self.__pv_playcontrol,0)

  def status(self,verbose=True):
    ret=Pv.get(self.__pv_playstatus)
    ret = self.__status[ret]
    if (verbose):
      print "Mode: %s" % self.getmode()
      print "Current status: %s" % ret
    else:
      return ret

  def wait(self,verbose=False):
    sleep(0.01)
    mode = self.getmode()
    if (mode  == "Repeat N Times"):
      ntodo  = self.__getnrepeats_to_do()
      while ( (Pv.get(self.__pv_playstatus) != 0) or (Pv.get(self.__pv_total_count) < ntodo) ):
        n = self.__getnpulses_in_play()
        if (verbose):
          print "running (%d of %d) ...\r" % (n,ntodo)
        sleep(0.01)
      n = self.__getnpulses_in_play()
      if (verbose): print "done (%d) ...\r" % n
      return
    elif (mode == "Once"):
      ntodo = 1
      while ( (Pv.get(self.__pv_playstatus) != 0) or (Pv.get(self.__pv_total_count) != self.__total_count+1) ):
        if (verbose):
          print "running (%d) ...\r" % (ntodo)
        sleep(0.01)
      n = self.__getnpulses_in_play()
      if (verbose): print "done (%d) ...\r" % n
      return

  @if_owner
  def update(self, wait=False):
    # notify the machine EVG of the changes
    ec = tuple(map(int,self.__ec))
    bd = tuple(map(int,self.__bd))
    fd = tuple(map(int,self.__fd))
    bc = tuple(map(int,self.__bc))

    Pv.put(self.__pv_EC_array, ec)
    Pv.put(self.__pv_BD_array, bd)
    Pv.put(self.__pv_FD_array, fd)
    Pv.put(self.__pv_BC_array, bc)

    Pv.wait_for_value(self.__pv_EC_array, ec, timeout=1)
    Pv.wait_for_value(self.__pv_BD_array, bd, timeout=1)
    Pv.wait_for_value(self.__pv_FD_array, fd, timeout=1)
    Pv.wait_for_value(self.__pv_BC_array, bc, timeout=1)

    if wait:
      self.reset_update_cb()
    Pv.put(self.__pv_notify,1)
    if wait:
      self.wait_update_cb()

  def _init_update_cb(self):
    """
    Initialize event callback on update.
    """
    self._update_pv = Pv.Pv(self.__pv_notify, initialize=True, monitor=True)
    self._update_pv.add_monitor_callback(self._update_cb)
    self._update_event = Event()

  def _update_cb(self, e=None):
    """
    Flag event sequencer as updated
    """
    if e is None:
        self._update_event.set()

  def reset_update_cb(self):
    """
    Reset update event callback.
    """
    self._update_event.clear()

  def wait_update_cb(self, timeout=None):
    """
    Wait for update event callback.
    """
    self._update_event.wait(timeout)
