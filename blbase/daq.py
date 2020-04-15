from blutil import notice, guessBeamline
from blutil import config
from blutil.peakanalysis import PeakAnalysis
from blutil.plot import Plot2D
from detectors_pyami import PYAMIdetector
import beamline
import pydaq
import psp.Pv as Pv
import sys
import signal
import motor
import virtualmotor
import pvmotor
import time
import os
import re
import glob
import pyami
import pylab
import daqFit
import socket
import numpy as np
from datetime import datetime
import xml.etree.ElementTree as ET


class Daq:
  def __init__(self,host,platform=0,lcls=None,feedbackPVs=None, sequencer=None):
    self._host=host
    self._platform=platform
    self.__daq = None
    self.__scanstr = None
    self.__monitor=None
    self.__dets = None
    self.__filter_det = None
    self.__filter_min = None
    self.__filter_max = None
    self.__filter_string = None
    self.__npulses = None
    self.__running=False
    self.__config = {
        'events': 0,
        'controls': [],
        'monitors': [],
        'labels': [],
        'key': None,
        'use_l3t': False,
        'partition': None,
        'duration': None,
        'record': None,
    }
    self.__states = [
        'Disconnected',
        'Connected',
        'Configured',
        'Open',
        'Running'
    ]
    self.__connect_state = self.__states.index('Connected')
    self.__config_state = self.__states.index('Configured')
    self.__configured_fallback=False 
    self.issingleshot=0
    self.plot=None
    self.doplot=True
    self.record=None
    self.scan_in_ext_window=False
    self.settling_time = 0.
    self._scanlog_dir = config.scandata_directory
    self._scanlog_mode = config.scandata_mode
    if self._scanlog_mode == "append":
        self._scanlog_file = config.scandata_file
    if self._scanlog_mode not in ("append", "new_files"):
        print "WARNING: scan log files not initialized properly in config."
    self.__l3tdir = "/reg/neh/operator/" + guessBeamline() + "opr/l3t"
    self.__l3tdefault = os.path.join(self.__l3tdir, 'amifil.l3t')
    self.__l3tseldefault = os.path.join(self.__l3tdir, 'amisel.l3t')
    self.fit = daqFit.Fit(self,daqFit.functions)
    self.lcls = lcls
    self.__averaging = False
    if feedbackPVs is None:
      self._feedbackPVs = {}
    else:
      self._feedbackPVs = feedbackPVs
    self.feedback = EpicsFeedback(self._feedbackPVs)
    self.reset_readout_checks()
    self._sequencer = sequencer

  def set_monitor(self,det=None):
    """
    Normalize plot data to the output of det. det=None means no monitor.
    """
    if (det is None):
      self.__monitor=None
      return
    try:
      det.name
    except:
      print "The detector used for monitor is not right"
    self.__monitor = det

  def set_filter(self,*k,**kw):
    """ enable data filtering:
        usage:
        set_filter(); remove filtering
        set_filter(min,max); enable filtering between min and max on the monitor
        set_filter(det,min,max); enable filtering using det
    """
    l3t_name=kw.get('l3t_name', self.__l3tdefault)
    if l3t_name.find(guessBeamline() + 'opr')<=0:
      l3t_name = os.path.join(self.__l3tdir, l3t_name)
    orEvtCode=kw.get('orEvtCode',[162])
    if len(k)==0:
      if self.__filter_det is not None:
        self.__filter_det = None
        self.__filter_min = None
        self.__filter_max = None
        self.__filter_string = None
      self.set_selection()
    elif len(k) == 2:
      if self.__monitor is None:
        print "Monitor is not defined, no filter set!"
      else:
        self.__filter_det = self.__monitor
        self.__filter_min = k[0]
        self.__filter_max = k[1]
        self.__filter_string = "%f<%s<%f" % (k[0],self.__filter_det.aminame,k[1])
        print "Filter string is '%s'" % self.__filter_string

        self.set_selection(self.__filter_det.aminame,k[0],k[1],l3t_name=l3t_name,orEvtCode=orEvtCode)
    elif len(k) == 3:
      self.__filter_det = k[0]
      self.__filter_min = k[1]
      self.__filter_max = k[2]
      self.__filter_string = "%f<%s<%f" % (k[1],k[0].aminame,k[2])
      print "Filter string is '%s'" % self.__filter_string
      self.set_selection(self.__filter_det.aminame,k[1],k[2],l3t_name=l3t_name,orEvtCode=orEvtCode)
    else:
      print "Unsupported number of arguments. Supply no arguments to clear filter, or 3 arguments to set it!"

  def set_detectors(self,*dets):
    """
    Set up scans to always check these dets, even if not explicitly passed as
    arguments to the scans. Call with no arguments to clear the dets list.
    """
    ok = True
    if dets is None or len(dets) == 0:
      self.__dets=None
      print "Detectors list cleared"
    else:
      for i in range(len(dets)):
        if not isinstance(dets[i],PYAMIdetector):
          ok=False
          print "\nWARNING:  Parameter %u is not a valid detector!  Request ignored." % (i+1)
      if ok:
        self.__dets=dets

  def set_selection(self,*k,**kw):
    """
    set pyami trigger filter
    """
    l3t_name=kw.get('l3t_name', self.__l3tseldefault)
    if len(k) == 3 :
      if isinstance(k[0],basestring):
        trigger_str = "%f<%s<%f" % (k[1],k[0],k[2])
      else:
        trigger_str = "%f<%s<%f" % (k[1],k[0].aminame,k[2])

      orEvtCode=kw.get('orEvtCode',[])
      if len(orEvtCode)>0:
        new_trigger_str = "(%s)"%trigger_str
        for evtCode in orEvtCode:
          new_trigger_str = "%s|(0.1<DAQ:EVR:Evt%d<2)"%(new_trigger_str,evtCode)
        trigger_str = new_trigger_str 

      pyami.set_l3t(trigger_str, l3t_name)
      print 'L3 trigger string: ',trigger_str
    else:
      self.clear_daq_l3t()

  def status(self):
    """
    Return status string
    """
    s  = "DAQ status\n"
    s += "  default DETECTORS read in scan : "
    if (self.__dets is None):
      s += "  NONE\n"
    else:
      for d in self.__dets: s += " %s " % d.name
      s+="\n"
    s += "  MONITOR used for normalization : "
    if (self.__monitor is None):
      s += "  NONE\n"
    else:
      s += " %s\n" % self.__monitor.name
    s += "  FILTERING : "
    if (self.__filter_det is None):
      s += "  NONE\n"
    else:
      s += " %f<%s<%f\n" % (self.__filter_min,self.__filter_det.name,self.__filter_max)
    if (self.record is None):
      s += "  Recording RUN: selected by GUI\n"
    elif (self.record):
      s += "  Recording RUN: YES\n"
    elif (not self.record):
      s += "  Recording RUN: NO\n"
    s += "  SETTLING time after motor movement: %.3f sec\n" % self.settling_time
    return s

  def __repr__(self):
    return self.status()

  def _get_filter(self):
      return (self.__filter_det,(self.__filter_min,self.__filter_max))
  filter = property(_get_filter)

  @property
  def __configured(self):
    if self.__daq is None:
      return False
    elif hasattr(pydaq.Control, 'state'):
      return self.__daq.state() >= self.__config_state
    else:
      return self.__configured_fallback

  @property
  def __connected(self):
    if self.__daq is None:
      return False
    elif hasattr(pydaq.Control, 'state'):
      return self.__daq.state() >= self.__connect_state
    else:
      return True

  @property
  def state(self):
    if hasattr(pydaq.Control, 'state'):
      if self.__daq is None:
        return self.__states[0]
      else:
        return self.__states[self.__daq.state()]
    else:
      return 'Unknown'

  def connect(self, newDAQ=False):
    """
    Connect this python session to the daq. Only one python session can
    connect to a daq at a time.
    """
    print "con state:", self.__connected
    if self.__daq != None and (newDAQ or not self.__connected):
      self.disconnect()
    if self.__daq == None:
      try:
        self.__daq = pydaq.Control(self._host,self._platform)
        self.__daq.connect()
        print 'Connected to DAQ'
      except:
        self.__daq = None
        print 'Failed to connect to DAQ - check that it is up and allocated'
    try:
      beamline.daqconfig.create(self.__daq)
    except:
      pass
    return self.__daq

  def disconnect(self):
    """
    Disconnect this python session from the daq.
    """
    sys.stdout.flush()
    try:
      beamline.daqconfig.unlock()
    except:
      pass
    if self.__daq != None:
      self.__daq.disconnect()
      del self.__daq
      self.__daq = None
    self.__configured_fallback = False

  def daqconnect(self):
    """
    Bypass this interface and connect the pydaq.Control object.
    """
    self.__daq.connect()
    return self.__daq

  def daqdisconnect(self):
    """
    Bypass this interface and disconnect the pydaq.Control object.
    """
    self.__daq.disconnect()

  def clear_daq_l3t(self):
    """
    clear pyami l3t filtering.
    """
    pyami.clear_l3t()

  def __check_config(self,**kwargs):
    """
    Check if the DAQ needs to be configured
    """
    if (self.__daq is None or not self.__configured):
      self.configure(**kwargs)
    elif kwargs.get('newDAQ', False):
      self.configure(**kwargs)
    elif self.record != self.__config['record']:
      self.configure(**kwargs)
    else:
      for key, val in kwargs.iteritems():
        if key in self.__config:
          if val != self.__config[key]:
            self.configure(**kwargs)
            break
        else:
          raise KeyError('Unknown daq configuration key: %s'%key)

  def __cache_config(self,**kwargs):
    """
    Update the cache DAQ configuration data
    """
    for key, val in kwargs.iteritems():
      if key in self.__config:
          self.__config[key] = val
      else:
          raise KeyError('Unknown daq configuration key: %s'%key)

  def __check_dets(self,dets):
    """
    Given a list of dets to use in a scan, add monitor and filter dets
    and set this up correctly. Return the augmented list of dets.
    """
    try:
      if (type(dets[0]) is tuple): dets=dets[0]
    except:
      pass
    dd = []
    for i in range(len(dets)):
      if (self.__monitor != dets[i]): dd.append(dets[i])
    if (self.__dets is not None):
      for i in range(len(self.__dets)):
        if (self.__monitor != self.__dets[i]): dd.append(self.__dets[i])
    if (self.__monitor is not None):
      try :
        dd.index(self.__monitor)
      except:
        dd.append(self.__monitor)
    if (self.__filter_det is not None):
      filter_aminame = self.__filter_det.aminame
      filter_str = "%f<%s<%f" % (self.__filter_min,filter_aminame,self.__filter_max)
      for i in range(len(dd)):
        dd[i].pyamiE = pyami.Entry(dd[i].aminame,"Scalar",filter_str)
    else:
      for i in range(len(dd)):
        dd[i].pyamiE = pyami.Entry(dd[i].aminame,"Scalar")
    return dd

  def __start_av(self,dets):
    """
    Tell pyami to start looking at events for dets.
    """
    #t0=time.time()
    if len(dets)!=0:
      for det in dets:
        det.connect(self.__filter_string)
        if self.__averaging or self.__running:
          try:
            det.clear()
          except:
            pass
    self.__averaging = True
    #if (config.TIMEIT):
    #  print "time needed for __start_av: %.3f" % (time.time()-t0)

  def __normalize(self,det,mon):
    """
    Normalize det data dictionary using mon data dictionary.
    """
    try:
      det["mean"] /= mon["mean"]
      det["err"] = det["err"]/mon["mean"]+np.abs(det["mean"]/mon["mean"])**2*mon["err"]
    except ZeroDivisionError:
      det["mean"]=np.nan
      det["err"]=np.nan
    return det

  def __stop_av(self,dets):
    """
    Get the average of events on dets since __start_av was last called.
    """
    #t0=time.time()
    ret = ""
    retv=dict()
    if (self.__monitor is not None):
      mon = dets[-1].get()
    try:
      if len(dets)!=0:
        for det in dets:
          v=det.get()
          try:
            det.clear()
          except:
            pass
          if ( (self.__monitor is not None) & (det != self.__monitor) ):
            v=self.__normalize(v,mon)
          retv[det]=v
          ret += "|%+11.4e %+11.4e" % (v["mean"],v["err"])
          try:
            self.__y[det].append(v["mean"])
            self.__e[det].append(v["err"])
          except:
            pass
    except:
      pass
    self.__averaging = False
    try:
      ret += "| %.2f" % ( float(v["entries"])/self.__npulses*100)
    except:
      pass
    #if (config.TIMEIT>0):
    #  print "time needed for __stop_av: %.3f" % (time.time()-t0)
    return ret,retv

  def configure(self,events=0,controls=[],monitors=[],labels=[],key=None,use_l3t=False,newDAQ=False,partition=None,duration=None):
    """ note: controls,monitors and labels have to be list of tuple
        and NOT list of list """
    if self.connect(newDAQ=newDAQ) is None:
        raise RuntimeError('Failed to connect to DAQ - check that it is up and allocated')
    #insert call for trigger here
    #if (self.__filter_det is not None):
    #  filter_aminame = self.__filter_det.aminame
    #  filter_str = "%f<%s<%f" % (self.__filter_min,filter_aminame,self.__filter_max)
    if key==None:
      key = self.__daq.dbkey()
      #this is something that happened during the 5th shift of Khalil (xppj6715)....now we print an explicit warning
      if key == 0:
        print "got a key of 0, this is not going to work!"
      else:
        print "in configure, got key 0%x from daq"%key
    kwargs = {"key":key, "controls":controls, "monitors":monitors, "labels":labels}
    if self.record is None:
      print "Record is what you set in GUI"
    else:
      kwargs["record"] = bool(self.record)
      print "Record is: " , bool(self.record), " (l3t)"
    if duration is None:
      if use_l3t:
        kwargs["l3t_events"] = events
      else:
        kwargs["events"] = events
    else:
      sec = int(duration)
      nsec = int((duration-sec)*1e9)
      kwargs["duration"] = [sec,nsec]
    if partition is not None:
      kwargs["partition"] = partition
    self.__daq.configure(**kwargs)
    self.__cache_config(events=events,
                        controls=controls,
                        monitors=monitors,
                        labels=labels,
                        key=key,
                        use_l3t=use_l3t,
                        partition=partition,
                        duration=duration,
                        record=self.record)
    self.__configured_fallback = True

  def begin(self,events=None,duration=None,controls=[],monitors=[],labels=[],use_l3t=False):
    if (self.__daq is None or not self.__configured):
      self.configure(events=events,controls=controls,monitors=monitors,labels=labels,use_l3t=use_l3t)
    self.__running=True
    if (duration is not None):
      sec = int(duration)
      nsec = int ( (duration-sec )*1e9 )
      duration = [sec,nsec]
      self.__daq.begin(duration=duration,controls=controls,monitors=monitors,labels=labels)
    elif (events is not None):
      if use_l3t:
        self.__daq.begin(l3t_events=events,controls=controls,monitors=monitors,labels=labels)
      else:
        self.__daq.begin(events=events,controls=controls,monitors=monitors,labels=labels)
    else:
      self.__daq.begin(controls=controls,monitors=monitors); # use default number of events set with configure

  def wait(self):
    """
    Halt the thread until the daq is done.
    """
    if (self.__running):
      self.__daq.end()
      self.__running=False

  def endrun(self):
    """
    End the current run.
    """
    if (self.__daq is not None):
      self.__daq.endrun()

  def stop(self):
    """
    Interrupt data collection and stop.
    """
    if (self.__running):
      self.__daq.stop()
      try:
        self.__daq.end()
      except RuntimeError:
        pass
      self.__running=False

  def experiment(self):
    """
    Return the current experiment, or 0 if not connected.
    """
    if (self.__daq is not None):
      return self.__daq.experiment()
    else:
      return 0

  def runnumber(self):
    """
    Return the current run number, or 0 if not connected.
    """
    if (self.__daq is not None):
      return self.__daq.runnumber()
    else:
      return 0

  def eventnum(self):
    """
    Return the current event number, or 0 if not connected.
    """
    if (self.__daq is not None) and self.__running:
      return self.__daq.eventnum()
    else:
      return 0

  def dbalias(self):
    """
    Return the database alias, or empty string if not connected.
    """
    if (self.__daq is not None):
      return self.__daq.dbalias()
    else:
      return ""

  def dbkey(self):
    """
    Return the database key, or 0 if not connected.
    """
    if (self.__daq is not None) and self.__running:
      return self.__daq.dbkey()
    else:
      return 0

  def dbpath(self):
    """
    Return the database path, or empty string if not connected.
    """
    if (self.__daq is not None):
      return self.__daq.dbpath()
    else:
      return ""

  def getPartition(self, printThis=False):
    """
    Return a dictionary with information about the daq partition.
    """
    if (self.__daq is None):
      if raw_input('We are not connected to the DAQ, would you like to connect to check?(y/n)') is 'y':
        self.connect()
    if (self.__daq is not None):
      return self.__daq.partition()
    else:
      print 'could not find the partition, return None'

  def getReadoutNodes(self, printThis=False, onlyRec=False):
    """
    Return a list of readout nodes.
    """
    nodes = self.getPartition()['nodes']    
    if printThis:
      for device in nodes:
        if device['record'] or not onlyRec:
          print device['id'],' is recorded ',device['record']
    return nodes

  def get_l3file(self):
    """
    Return the name of the l3_file, and the filter text if possible.
    """
    l3_file = self.getPartition()['l3path']
    if os.path.isfile(l3_file):
      root = (ET.parse(l3_file)).getroot()
      filt_text = root.find('AbsFilter').find('text').text
      return [l3_file, filt_text]
    else:
      return [l3_file]

  def get_l3use(self):
    """
    Return 2 if l3veto, 1 if l3tag, and 0 otherwise.
    """
    #l3_unbiased = self.getPartition()['l3unbiasedFraction']
    if self.getPartition()['l3veto']:
      return 2
    if self.getPartition()['l3tag']:
      return 1
    return 0
    
  def isRecording(self):
    """
    Return True if the daq was set to record when we first connected to it.
    """
    if (self.__daq is None):
      if raw_input('We are not connected to the DAQ, would you like to connect to check?(y/n)') is 'y':
        self.connect()
    if (self.__daq is not None):
      return self.__daq.record()
    return False

  def calibcycle(self,events=None,controls=[],monitors=[],use_l3t=False,use_sequencer=False):
    #t0=time.time()
    self.__npulses=events
    if (self.__daq is None or not self.__configured):
      self.configure(events=events,controls=controls,monitors=monitors,use_l3t=use_l3t)
    self.begin(events=events,controls=controls,monitors=monitors,use_l3t=use_l3t)
    if use_sequencer:
      if self._sequencer is None:
        print "WARNING: Sequencer option selected, but no sequencer passed into daq constructor!"
      else:
        if use_sequencer == 1:
          self._sequencer.modeOnce()
        elif use_sequencer == -1:
          self._sequencer.modeForever()
        else:
          self._sequencer.modeNtimes(use_sequencer)
        self._sequencer.start()
    self.wait()
    if use_sequencer and self._sequencer is not None:
      self._sequencer.stop()
    #tneeded = time.time()-t0
    #if (config.TIMEIT>0):
    #  print "Daq.calibcycle: time needed for %d shots: %f" % (events,tneeded)

  def __prepare_plot(self,dets):
    """
    Clear leftover plot data.
    """
    plotID=1
    self.__y=dict()
    self.__e=dict()
    self.__x=[]
    for det in dets:
      self.__y[det]=[]
      self.__e[det]=[]
    return plotID

  def __prepare_dets_title(self,dets):
    """
    Given a list of dets, prepare text for scan readbacks.
    """
    line1 = ""
    line2 = ""
    for det in dets:
      line1 += "|%s" % det.name.center(23)
      line2 += "|%s" % "avg".center(11)
      line2 += " %s" % "err".center(11)
    line1+="|"
    line2+="|%pulses"
    return line1,line2

  def ct(self,sec,*dets):
    """ like spec ct (the DAQ has to be started) ... """ 
    ## take care of the detectors
    dets=self.__check_dets(dets)

    # start monitoring ...
    self.__start_av(dets)
    time.sleep(sec)
    rep = self.__stop_av(dets)

    print "   number of sec per point: %.3f (got" % sec,
    for det in dets:
      print " %d" % rep[1][det]["num"],
    print " shots)"
    line1,line2 = self.__prepare_dets_title(dets)
    print "%5s%s" % ('',line1)
    print "%5s%s" % ("point",line2)
    cycle = 0
    print "%5d%s" % ( (cycle+1),rep[0] )

  def takeshots(self, events, *dets, **kwargs):
    """
    Do a run with a certain number of events (starting/stopping the DAQ)

    Parameters
    ----------
    events : int
        Number of events to take

    *dets : detector objects, optional
        Detectors to display values in python

    **kwargs : options, optional
        use_l3t : bool, default False
            If True, we'll use the l3t filter.

    Returns
    -------
    detector_avg : list of floats
        The time-averaged values of *dets from this run.
    """ 
    # Parse kwargs
    use_l3t = kwargs.get("use_l3t", False)

    ## take care of the detectors
    dets = self.__check_dets(dets)
    ## take care of configurattion
    self.__check_config(events=events, use_l3t=use_l3t)

    print "Taking {} shots... Press ctrl+c to interrupt.".format(events)
    
    try:
        self.__start_av(dets)
        self.calibcycle(events, use_l3t=use_l3t)
    except Exception:
        sys.excepthook(*sys.exc_info())
        print "Error in takeshots!"
    finally:
        self.endrun()
        ret, retv = self.__stop_av(dets)

    # If we had *dets, we can show data like actual # of events, etc.
    if len(dets)!=0:
      for det in dets:
        print "| %s" % (det.name+"(avg)").rjust(15),
        print " %s" % (det.name+"(err)").rjust(15),
      print "| %pulses"
      for det in dets:
        info = retv[det]
        print "|%+16.4e %+16.4e" % (info["mean"], info["err"]),
      print "| %.2f" % (100.*retv[dets[0]]["entries"]/self.__npulses)
      print "Scalar data from {} shots".format(retv[dets[0]]["entries"])
      return [retv[d]["mean"] for d in dets]

  def test(self,sec,*dets):
    print globals()
    print locals()
    """ like spec timescan """
    str = guessBeamline() + "daq.test(%d" % sec
    for d in dets:
      str+=",d.%s" % d.name
    str +=")"
    print str
#    config.logbook.submit(str,tag="scan")

  def takeshots_runningMotor(self,motor,interval,Nevents,acctime=.1,timeout=1,goback=False):    
    motname = motor.name
    motspeedorig = motor.get_speed()
    pulsefreq = self.lcls.get_fburst()
    start_pos = motor.wm()
    motspeed = 1.*np.abs(interval) * pulsefreq # in motor units / s
    total_range = acctime*2*motspeed * np.sign(interval) + 1.* (Nevents-1) * interval
    controls = []
    controls.append((motname+'_start',start_pos))
    controls.append((motname+'_speed',motspeed))
    controls.append((motname+'_acctime',acctime))
    controls.append(('beamRate',pulsefreq))
    controls.append(('N_requested_events',Nevents))
    # do stuff
    print "doing stuff"
    self.lcls.set_nburst(Nevents)

    motor.set_speed(motspeed)
    time.sleep(.02)
    t0 = time.time()
    while (np.abs(motor.get_speed()/motspeed-1) > .1):
      if (time.time()-t0)> timeout:
        print "Timed out in takeshots_runningMotor, could not set desired speed!!"
        return
      else:
        time.sleep(.01)

    motor.move_relative(total_range)
    time.sleep(acctime)
    self.lcls.get_burst()
    motor.wait()
    arrived_pos = motor.wm()
    controls.append((motname+'_end',arrived_pos))
    motor.set_speed(motspeedorig)
    if goback:
      motor.move(start_pos)
      motor.wait()
    #t0 = time.time()
    #while (np.abs(motor.get_speed()/motspeedorig-1) > .1):
      #print np.abs(motor.get_speed()/motspeedorig-1)
      #if (time.time()-t0)> timeout:
        #print "Timed out in takeshots_runningMotor!!"
        #print "blue"
        #print motspeedorig
        #print motor.get_speed()
        #return
      #else:
        #time.sleep(.01)
    return controls

  def controls_runningMotor(self,motor,interval,Nevents,acctime=.1,timeout=1,goback=False):    
    motname = motor.name
    pulsefreq = self.lcls.get_fburst()
    start_pos = motor.wm()
    motspeed = 1.*np.abs(interval) * pulsefreq # in motor units / s
    total_range = acctime*2*motspeed * np.sign(interval) + 1.* (Nevents-1) * interval
    controls = []
    controls.append((motname+'_start',start_pos))
    controls.append((motname+'_speed',motspeed))
    controls.append((motname+'_acctime',acctime))
    controls.append(('beamRate',pulsefreq))
    controls.append(('N_requested_events',Nevents))
    controls.append(('goback',goback))
    return controls

  def timescan(self,sec,*dets):
    """ like spec timescan """
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## get ready for plot
    plotid=self.__prepare_plot(dets)
    self.plot=Plot2D(plotid)
    self.__scanstr = "#   integration time per point: %.3f\n" % sec
    line1,line2 = self.__prepare_dets_title(dets)
    self.__scanstr += "#%5s%s\n" % ('',line1)
    self.__scanstr += "#%5s%s" % ("point",line2)
    print self.__scanstr,
    cycle=0
    while(1):
      # start monitoring ...
      self.__start_av(dets)
      time.sleep(sec)
      rep = self.__stop_av(dets)
      str = "%5d%s" % ( (cycle+1),rep[0] )
      self.__scanstr += "%s\n" % str
      self.__x.append(cycle+1)
      if (cycle>2):
        self.plot.setdata(self.__x,self.__y[dets[0]])
#        myplot.update()
      cycle=cycle+1

  def __ascan(self,tMot,tPos,events_per_point,*dets,**opts):
    isburst = opts.get("isburst", False)
    shotsmovingmotor = opts.get("shotsmovingmotor", None)
    use_l3t = opts.get("use_l3t", False)
    debug = opts.get("debug", 1)
    newDAQ = opts.get("newDAQ", False)
    use_sequencer = opts.get("sequencer", False)
    extra_log_data = opts.get("log_data", None)

    if self.__daq is None:
        self.connect()

    if len(dets) == 0:
      print "Warning: No detectors selected! Nothing to plot!"
      print "Use daq.set_detectors to set defaults or put as argument in scan!"
 
    ### debug ###
    #if debug >=10:
    #  print "begin of __ascan in __ascan", str(datetime.now())

    try:
      if type(tMot) is not tuple:
        tMot = (tMot,)
        tPosMod = [(pos,) for pos in tPos  if ( (type(pos) is not tuple) and (type(pos) is not list) )]
      else:
        tPosMod = tPos

      for i, mot in enumerate(tMot):
        try:
          deadband = mot.get_par("retry_deadband")
        except: # virtual motors have no deadband
          continue
        try:
          step_size = tPos[1][i]-tPos[0][i]
        except:
          step_size = tPos[1]-tPos[0]
        deadband = abs(deadband)
        step_size = abs(step_size)
        if deadband > step_size:
          print "Warning! {0} deadband is {1}, greater than step size {2}".format(mot.name, deadband, step_size)
          print "There may be a problem!"

      ostr = "#%s" % self.status()
      if extra_log_data is not None:
        ostr += "\n " + str(extra_log_data) + "\n"
      ostr = ostr.replace("\n","\n#")
      if extra_log_data is not None:
        ostr += "\n"
      if ( self.__monitor is not None ):
        ostr += "#readings (except for monitor) are normalized\n"

      ## take care of the motor first
      initial_pos = []

      for m in tMot:
        initial_pos.append( m.wm() )
      sys.stdout.flush()
      self.__scanstr= ostr
      controls = []
      for m in tMot:
        controls.append( (m.name,m.wm()) )
      if shotsmovingmotor is not None:
        shotmot, shotmotint, shotmotgoback = shotsmovingmotor
        controls.extend(self.controls_runningMotor(shotmot,shotmotint,events_per_point))
      #print "calibcycle, controls=%s" % controls

      with EpicsFeedbackContext(self.feedback):

        # configure daq and test that it is sanely set up
        self.__check_config(events=events_per_point,controls=controls,use_l3t=use_l3t)
        if not self.__check_daq(use_l3t=use_l3t,debug=debug):
          return

        # write feedback PVs
        iStep=0
        self.write_feedback_pvs(tMot,tPosMod,events_per_point,iStep)
        # done writing feedback PVs

        if (len(dets) != 0):
          plotid=self.__prepare_plot(dets)
          self.plot=Plot2D(plotid)
          self.plot.set_xlabel(tMot[0].name)
          if ( self.__monitor is not None ):
            self.plot.set_ylabel(dets[0].name+'/'+self.__monitor.name)
          else:
            self.plot.set_ylabel(dets[0].name)
        for m in tMot:
          self.__scanstr+= "** Scanning  motor: %s (pvname: %s)\n" % (m.name,m.pvname)
        self.__scanstr+= "#   number of points: %d\n" % len(tPos)
        self.__scanstr+= "#   number of shots per point: %d\n" % events_per_point
        for i in range(len(tMot)): 
          if len(tMot)>1:
            self.__scanstr+="# step size for motor %s: %.4e\n" % (tMot[i].name,tPos[1][i]-tPos[0][i])
          else:
            self.__scanstr+="# step size for motor %s: %.4e\n" % (tMot[0].name,tPos[1]-tPos[0])
        self.__scanstr+="# Start time: %s\n" % self.getArchiverTimestamp()
        self.starttime = datetime.now()
        line1,line2 = self.__prepare_dets_title(dets)
        self.__scanstr += "#++%5s" % ("")
        for m in tMot: self.__scanstr += "%12s" % (m.name)
        self.__scanstr += "%s\n" % (line1)
        self.__scanstr += "# point|"
        for m in tMot: self.__scanstr += "%12s" % ("position")
        self.__scanstr += "%s\n" % (line2)
        print self.__scanstr,
        #snelson
        #debug = 15
        for cycle in range(len(tPos)):
          ### debug ###
          #if debug >= 15: print 'start with step', cycle
          t0cycle=time.time()
          pos = tPos[cycle];
          if ( (type(pos) is not tuple) and (type(pos) is not list) ):
            pos=(pos,)
          for i in range(len(pos)):
            tMot[i].move_silent(pos[i])
          for i in range(len(pos)):
            tMot[i].wait()
          sys.stdout.flush()
          if (self.settling_time != 0):
            time.sleep(self.settling_time)
          if (config.TIMEIT>0):
            print "time needed for moving and settling %.3f" % (time.time()-t0cycle)
          ### debug ###
          if debug >= 15: print 'start to average the detectors, appended to controls', cycle
          self.__start_av(dets)
          if debug >= 15: print 'started to average the detectors, appended to controls', cycle
          time.sleep(0.05); # to make sure readback is uptodate (20ms)
          controls=[]
          for m in tMot:
            controls.append( (m.name,m.wm()) )
          #print "calibcycle, controls=%s" % controls
          ### debug ###
          if debug >= 15: print 'begin cycle', cycle
          if shotsmovingmotor is not None:
            self.begin(events=events_per_point,controls=controls, use_l3t=use_l3t)
            self.takeshots_runningMotor(shotmot,shotmotint,events_per_point,goback=shotmotgoback)
            self.wait()
          elif isburst:
            self.begin(events=events_per_point,controls=controls, use_l3t=use_l3t)
            self.lcls.get_burst(events_per_point)
            self.wait()
          else:
            self.calibcycle( events_per_point, controls=controls, use_l3t=use_l3t, use_sequencer=use_sequencer )
          ### debug ###
          #if debug >= 15: print 'daq cycle', cycle, 'ended'
          ret = self.__stop_av(dets)
          ### debug ###
          #if debug >= 15: print 'get detector information for cycle:', cycle
          ostr = "%7d" % (cycle+1)
          ### debug ###
          #if debug >= 15: print 'print cycle for motor string:', cycle
          for m in tMot:
            ### debug ###
            #if debug >= 15: print 'motor', m.pvname
            ostr+="|%12.5e" % (m.wm())
          ### debug ###
          #if debug >= 15: 'print motor pos for motor string:', cycle
          ostr += "%s" % (ret[0])
          ### debug ###
          #if debug >= 15: 'appended stuff to motor string in cycle', cycle
          print ostr
          sys.stdout.flush()
          self.__scanstr+="%s\n" % ostr
          #t0plots=time.time()
          ### debug ###
          #if debug >= 15: print 'now update plot in cycle', cycle
          if ( len(dets) != 0 ):
            self.__x.append(pos[0])
            if ( cycle>1 ):
              self.plot.setdata(self.__x,self.__y[dets[0]])
          #if (config.TIMEIT>0):
          #  print "time needed for updating plot %.3f" % (time.time()-t0plots)
          #if (config.TIMEIT>0):
          #  print "time needed for complete scan point %.3f" % (time.time()-t0cycle)
          ### debug ###
          #if debug >= 15: print 'now update istep PV in', cycle
          iStep+=1
          self.write_feedback_step_pvs(iStep)
          ### debug ###
          #if debug >= 15: 'done with step', cycle
        runn = "#   run number (0 = not saved): %d\n" % self.runnumber()
        self.__scanstr+=runn
        print runn
        #for i in range(len(tMot)):
          #print "Moving back %s to initial position (%e)..." % (tMot[i].name,initial_pos[i])
          #tMot[i].move_silent(initial_pos[i])
          #print " ... done"
          #pass
    finally:
      endtime = "# End time: %s\n" % self.getArchiverTimestamp()
      self.__scanstr += endtime
      self.savelog()
      self.endrun()

  def savelog(self):
    folder = self._scanlog_dir
    if self._scanlog_mode == "append":
      self.savetxt(folder + self._scanlog_file, "a")
    elif self._scanlog_mode == "new_files":
      t = self.starttime
      filename = "%04d-%02d-%02d_%02dh%02dm%02ds_run%04d.dat" % (t.year, t.month, t.day, t.hour, t.minute, t.second, self.runnumber())
      self.savetxt(folder + filename, "w")
    else:
      print "No valid option for scan logging found. Skipping save..."

  def scan_data(self, index):
    return self.__y[self.__dets[index]]
  
  def scan_pos(self, index):
    return self.__x

  def scan_err(self, index):
    return self.__e[self.__dets[index]]

  def ascan_repeat(self,mot,a,b,points,events_per_point,repeats,*dets,**opts):
    ## take care of the detectors
    dets=self.__check_dets(dets)
    pos=[]
    for i in range(repeats):
      for cycle in range(points+1):
        pos.append( (b-a)*cycle/float(points) + a )
    self.__ascan(mot,pos,events_per_point,*dets,**opts)

  def __check_mot(self,mot):
    if isinstance(mot, motor.Motor) \
           or isinstance(mot, virtualmotor.VirtualMotor):
      m = mot      
    else:
      m=pvmotor.PvMotor(mot,mot)
    return m

  def __check_daq(self, use_l3t=0, debug=0):
    if debug >=10:
      print "__ascan: check recording", str(datetime.now())
    if not self.isRecording():
      print 'We will not be recording this scan!'
    else:
      nodes = self.getReadoutNodes(printThis=True,onlyRec=True)
      haveNode = []
      for name in self.readout_checks:
        haveNode.append(False)
      for i, name in enumerate(self.readout_checks):
        for node in nodes:
          if node['id'].find(name)>=0:
            haveNode[i]=True
      for i, name in enumerate(self.readout_checks):
        if (not haveNode[i]) and raw_input('No {0} in partition, continue? (y/n)'.format(name)) != 'y':
          return False

    if debug >=10:
      print "__ascan: check l3 trigger", str(datetime.now())
    if use_l3t:
      #check that l3t is in configuration.
      if self.get_l3use()==0:
        print 'the l3t is not in the configuration, please fix or set use_l3t to false in scan call!'
        return
      filt_str = self.get_l3file()
      #I believe the DAQ protects against this, but better safe than sorry
      if len(filt_str)<2:
        print 'the trigger file was not defined'
      if self.get_l3use()>1:
        print 'we will only record events passing:', filt_str[1]
      else:
        print 'we will only count events passing:', filt_str[1]      
    return True

  def add_readout_checks(self, *nodes):
    """Add entries to the list of readout nodes that we check before scans."""
    self.readout_checks.extend(nodes)

  def reset_readout_checks(self):
    """Put our readout node checks back to default."""
    self.readout_checks = ['EpicsArch', 'BldEb'] 

  def ascan(self,mot,a,b,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first
    # if we send a real motor
    mot = self.__check_mot(mot)
    mot_and_pos = [ ( mot,mot.wm() ) ]
    pos=[]
    if type(points) is int:
      for cycle in range(points+1):
        pos.append( (b-a)*cycle/float(points) + a )
    elif type(points) is float:
      print "Interval parameter is interpreted as interval"
      pos = np.arange(a,b+points,np.sign(b-a)*np.abs(points))
      pos = list(pos)
    else:
      print "Attention: Interval parameter not understood!!!"
      return
      
    try:
      self.__ascan(mot,pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      print 'scan interrupted'
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def ascan_with_list(self,mot,positions,events_per_point,*dets,**opts):
    """ Scan the motor by a list of positions (in user coordinates).""" 
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first
    # if we send a real motor
    mot = self.__check_mot(mot)
    mot_and_pos = [ ( mot,mot.wm() ) ]
    try:
      self.__ascan(mot,positions,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def write_feedback_pvs(self,tMot,tPos,events_per_point,initial_step):
    tPosarr = np.array(tPos)
    self.feedback.writeField('istep', initial_step)
    self.feedback.writeField('isscan',1)
    for varno,mot in enumerate(tMot):
      self.feedback.writeField('var'+str(varno),mot.name)
      try:
        self.feedback.writeField('var'+str(varno)+'_min',np.min(tPosarr))
        self.feedback.writeField('var'+str(varno)+'_max',np.max(tPosarr))
      except Exception,e:
        print 'could not write feedback PVs '
        print e
        print tPosarr
        print tPos
    self.feedback.writeField('Nsteps',len(tPos))
    self.feedback.writeField('Nshots',events_per_point)  

  def write_feedback_step_pvs(self, step):
    self.feedback.writeField('istep', step)

  def cleanup(self,dets=None,mot_and_pos=None):
    """ mot_and_pos is a list of tuples [ (motor1,pos1), (motor2,pos2) , etc.] """
    #Pv.monitor_stop_all(clear=True)
    for el in mot_and_pos:
      m = el[0]; p = el[1]
      print "Moving the motor %s to initial position %.3e" % (m.name,p)
      m.move(p)
    print "Stopping scan and cleaning up"

  def a2scan(self,m1,a1,b1,m2,a2,b2,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()) ]
    pos=[]
    for cycle in range(points+1):
      p1 = (b1-a1)*cycle/float(points) + a1 
      p2 = (b2-a2)*cycle/float(points) + a2 
      pos.append( (p1,p2) )
    try:
      self.__ascan((m1,m2),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a2scan_with_list(self, m1, p1, m2, p2, events_per_point,*dets,**opts):
    """ Scan 2 motors at the same time defined by the position lists"""
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()) ]
    
    pos=[]
    for i in range(len(p1)):
      pos.append((p1[i], p2[i]))
    try:
      self.__ascan((m1,m2),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a3scan(self,m1,a1,b1,m2,a2,b2,m3,a3,b3,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    m3 = self.__check_mot(m3)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()), (m3,m3.wm()) ]
    pos=[]
    for cycle in range(points+1):
      p1 = (b1-a1)*cycle/float(points) + a1 
      p2 = (b2-a2)*cycle/float(points) + a2 
      p3 = (b3-a3)*cycle/float(points) + a3 
      pos.append( (p1,p2,p3) )
    try:
      self.__ascan((m1,m2,m3),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a3scan_with_list(self, m1, p1, m2, p2, m3, p3, events_per_point,*dets,**opts):
    """ Scan 3 motors at the same time defined by the position lists"""
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    m3 = self.__check_mot(m3)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()), (m3,m3.wm()) ]
    
    pos=[]
    for i in range(len(p1)):
      pos.append((p1[i], p2[i],p3[i]))
    try:
      self.__ascan((m1,m2,m3),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a4scan_with_list(self, m1, p1, m2, p2, m3, p3, m4, p4, events_per_point,*dets,**opts):
    """ Scan 4 motors at the same time defined by the position lists"""
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    m3 = self.__check_mot(m3)
    m4 = self.__check_mot(m4)
    
    pos=[]
    for i in range(len(p1)):
      pos.append((p1[i], p2[i],p3[i],p4[i]))
    try:
      self.__ascan((m1,m2,m3,m4),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a2scanmesh_with_list(self, m1, p1, m2, p2, events_per_point,*dets,**opts):
    """ Scan 2 motors at the same time defined by the position lists"""
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()) ]
    pos=[]
    for i in range(len(p1)):
      for j in range(len(p2)):
        pos.append((p1[i], p2[j]))
    try:
      self.__ascan((m1,m2),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def a3scanmesh_with_list(self, m1, p1, m2, p2, m3, p3, events_per_point,*dets,**opts):
    """ Scan 3 motors at the same time defined by the position lists"""
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    m3 = self.__check_mot(m3)

    pos=[]
    for i in range(len(p1)):
      for j in range(len(p2)):
        for k in range(len(p3)):
          pos.append((p1[i], p2[j], p3[k]))
    try:
      print 'now run the scan'
      self.__ascan((m1,m2,m3),pos,events_per_point,*dets,**opts)
      print 'now done with the scan'
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def dscan(self,mot,r1,r2,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    ## take care of the motor first
    # if we send a real motor
    mot = self.__check_mot(mot); mot.wait(); p = mot.wm()
    mot_and_pos=[(mot,p)]
    try:
       self.ascan(mot,p+r1,p+r2,points,events_per_point,*dets,**opts)
       print 'moving %s back to initial position %+4.f' % (mot.name,p)
       mot.mv(p)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def d2scan(self,m1,r11,r12,m2,r21,r22,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    ## take care of the motor first
    # if we send a real motor
    m1 = self.__check_mot(m1); m1.wait(); p1 = m1.wm()
    m2 = self.__check_mot(m2); m2.wait(); p2 = m2.wm()
    self.a2scan(m1,p1+r11,p1+r12,m2,p2+r21,p2+r22,points,events_per_point,*dets,**opts)

  def d3scan(self,m1,r11,r12,m2,r21,r22,m3,r31,r32,points,events_per_point,*dets,**opts):
    """ Scan the motor from a to b (in user coordinates) """ 
    ## take care of the detectors
    ## take care of the motor first
    # if we send a real motor
    m1 = self.__check_mot(m1); m1.wait(); p1 = m1.wm()
    m2 = self.__check_mot(m2); m2.wait(); p2 = m2.wm()
    m3 = self.__check_mot(m3); m3.wait(); p3 = m3.wm()
    self.a3scan(m1,p1+r11,p1+r12,m2,p2+r21,p2+r22,m3,p3+r31,p3+r32,points,events_per_point,*dets,**opts)

  def mesh2D(self,m1,a1,b1,n1,m2,a2,b2,n2,events_per_point,*dets,**opts):
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()) ]
    p1=[] 
    p2=[]
    for cycle in range(n1+1): p1.append( (b1-a1)*cycle/float(n1) + a1 )
    for cycle in range(n2+1): p2.append( (b2-a2)*cycle/float(n2) + a2 )
    pos = self.__make_mesh_motors_pos( (p1,p2) )
    try:
      self.__ascan((m1,m2),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def mesh3D(self,m1,a1,b1,n1,m2,a2,b2,n2,m3,a3,b3,n3,events_per_point,*dets,**opts):
    ## take care of the detectors
    dets=self.__check_dets(dets)
    ## take care of the motor first; if we send a real motor
    m1 = self.__check_mot(m1)
    m2 = self.__check_mot(m2)
    m3 = self.__check_mot(m3)
    mot_and_pos = [ (m1,m1.wm()), (m2,m2.wm()),(m3,m3.wm()) ]
    p1=[] 
    p2=[]
    p3=[]
    for cycle in range(n1+1): p1.append( (b1-a1)*cycle/float(n1) + a1 )
    for cycle in range(n2+1): p2.append( (b2-a2)*cycle/float(n2) + a2 )
    for cycle in range(n3+1): p3.append( (b3-a3)*cycle/float(n3) + a3 )
    pos = self.__make_mesh_motors_pos( (p1,p2,p3) )
    try:
      self.__ascan((m1,m2,m3),pos,events_per_point,*dets,**opts)
    except KeyboardInterrupt:
      self.cleanup(mot_and_pos=mot_and_pos)
    finally:
      self.cleanup(mot_and_pos=mot_and_pos)

  def __make_mesh_motors_pos(self,tPos):
    pos = []
    if len(tPos)==1:
      for p0 in tPos[0]:
        pos.append( [p0] )
    elif len(tPos)==2:
      for p0 in tPos[0]:
        for p1 in tPos[1]:
          pos.append( [p0,p1] )
    elif len(tPos)==3:
      for p0 in tPos[0]:
        for p1 in tPos[1]:
          for p2 in tPos[2]:
            pos.append( [p0,p1,p2] )
    return pos

  def getfilenamefromfile(self,fname):
    # assumes fname is a file containing a single line which is a filename, optionally trailed by at most a single newline
    return re.findall("^.*$", open(fname).readline())[0]    

  def savetxt(self,fname,mode='w'):
    str = "# %spython scan #\n" % guessBeamline()
    if ( self.__monitor is None ):
      str += "# Not normalized\n"
    else:
      str += "# normalization monitor: %s\n" % self.__monitor.name
      str += "# readings (except for monitor) are normalized\n"
    str += self.__scanstr.replace("|"," ")
    try:
      with open(fname, mode) as f:
        f.write(str)
    except Exception as e:
      print "Error writing log file {0}, {1}".format(fname, e)

  def getArchiverTimestamp(self):
    t = time.localtime()
    tstr = '"'+str(t[1])+'/'+str(t[2])+'/'+str(t[0])+' '+str(t[3])+':'+str(t[4])+':'+str(t[5])+'"'
    return tstr

  def restartDAQ(self,hostname=None):
    answer=raw_input("Sure ? ")
    if (answer[0].lower()=="y"):
      if hostname==None:
        hostname = socket.gethostname()
      restart_script = '/reg/neh/operator/' + guessBeamline() + 'opr/bin/' + guessBeamline() + 'restartdaq'
      if os.path.isfile(restart_script):
        os.system(restart_script)
      else:
        restart_script = 'source /reg/g/pcds/dist/pds/' +  guessBeamline() + '/scripts/restart_' +  guessBeamline() + '_daq.csh'
        if os.path.isfile(restart_script):
          os.system(restart_script)

  def bringup(self):
    os.system('/reg/neh/operator/' + guessBeamline() + 'opr/bin/' +
              guessBeamline() + '_cleanup_windows_daq')

  def loadtxt(self,*args):
    """
    Reads scandata saved py savetxt (NB: daq.py version, not numpy).
    The argument can either be the filname, a runnumber, or a negative 
    number defining -x scans ago (last saved scan would be -1). 
    If runnumber 0 is defined the newest unsaved run is displayed.
    """
    farg=args[0]
    if type(farg)==str:
      fina=farg
    else: 
      flist = glob.glob(self._scanlog_dir + '*.dat')
      flist.sort()
      runs = []
      for file in flist:
        runs.append(int(file.split('_run')[1].split('.dat')[0]))
      if farg>=0:
        fina = flist[runs.index(farg)]
      elif farg<0:
        fina = flist[farg]
    data = np.loadtxt(fina)
    return data

  def loadDaqDat(self,*args):
    """
    Reads scandata saved py savetxt (NB: daq.py version, not numpy).
    The argument can either be the filname, a runnumber, or a negative 
    number defining -x scans ago (last saved scan would be -1). 
    If runnumber 0 is defined the newest unsaved run is displayed.
    """
    farg=args[0]
    if type(farg)==str:
      fina=farg
    else: 
      flist = glob.glob(self._scanlog_dir + '*.dat')
      flist.sort()
      runs = []
      for file in flist:
        runs.append(int(file.split('_run')[1].split('.dat')[0]))
      if farg>=0:
        #print runs
        #print flist
        #print farg
        fina = flist[runs.index(farg)]
      elif farg<0:
        fina = flist[farg]
    file = open(fina)
    data = []
    motors = []
    detectors = []
    while 1:
      line = file.readline()
      if not line:
        break
      if line[0] is not '#':
        fields = line.split()
        try:
            data.append([float(field) for field in fields])
        except ValueError:
            print "Warning: possibly bad scan data file."
      if line[0:3]=='#**':
        motors.append(line.split('motor:')[1].split()[0])
      if line[0:3]=='#++':
        detectors = line.split()[2:]
    file.close()
    data = np.array(data)
    return data,motors,detectors

  def plotRun(self,run):
    """Plot previous Run"""
    [data,mot,det] = self.loadDaqDat(run)
    plotid=1
    self.plot=Plot2D(plotid)
    try:
      self.plot.set_xlabel(mot[0])
    except:
      pass    
    try:
      self.plot.set_ylabel(det[0])
    except:
      pass
    self.plot.setdata(data[:,1],data[:,2])
    try:
      self.__x = data[:,1]
      self.__y = dict()
      self.__e = dict()
      self.__y[det[0]] = data[:,2]
      self.__e[det[0]] = data[:,3]
    except:
      pass

  def backToEarth(self,nPoints=None):
    try:
      x,y = self.plot.getMostRecentData()
    except:
      x = np.arange(nPoints)
      y = np.ones(np.shape(x))
    plotid=1
    self.plot=Plot2D(plotid)
    self.plot.setdata(x,np.random.randn(len(y))*np.std(y)+np.mean(y))
    try:
      self.__x = data[:,1]
      self.__y = dict()
      self.__e = dict()
      self.__y[det[0]] = data[:,2]
      self.__e[det[0]] = data[:,3]
    except:
      pass

  def stopDAQ(self):
    answer=raw_input("Sure ? ")
    if (answer[0].lower()=="y"):
      restart_script = '/reg/neh/operator/' + guessBeamline() + 'opr/bin/' + guessBeamline() + 'stopdaq'
      if os.path.isfile(restart_script):
        os.system(restart_script)
      else:
        restart_script = 'source /reg/g/pcds/dist/pds/' + guessBeamline() + '/scripts/shutdown_' + guessBeamline() + '_daq.csh'
        if os.path.isfile(restart_script):
          os.system(restart_script)

  def analyzePlot(self,plotindex=-1):
    x,y=self.plot.plot.lines[plotindex].get_data()
    pylab.ion()
    fh=pylab.figure()
    pylab.plot(x,y,'ko-')
    CEN,FWHM,PEAK = PeakAnalysis(x,y,nb=3,plotpoints=True)
    print 'Center=%e; FWHM=%e, PEAK=%e' %(CEN,FWHM,PEAK)

    self.connect()
      
  def ScanTest(self,mot, det=None, newDAQ=False, use_l3t=True, debug=1, nCycle=3, nShots=60):
    icycle=0
    if nCycle<=1:
      print 'we need to run ober more than 1 cycle!',
      return
    while True:
      print 'ScanTest: cycle ',icycle
      if det:
        self.ascan(mot,0.,1.,nCycle-1,nShots,det,use_l3t=use_l3t, newDAQ=newDAQ, debug=debug)
      else:
        self.ascan(mot,0.,1.,nCycle-1,nShots,use_l3t=use_l3t, newDAQ=newDAQ, debug=debug)
      icycle+=1

  def DAQTestScan(self,nCycle,events_per_point,rawCmd=False, evtR=None):
    print 'DAQ Test Scan: Number of Steps: ',nCycle
    evtR.get()['mean']
    if rawCmd:
      self.connect()
      self.__daq.configure(events=events_per_point)
    else:
      self.configure(events_per_point, use_l3t=False)
    cycleMidTimes=[]
    cycleBeginTimes=[]
    cycleWaitTimes=[]
    for cycle in range(nCycle):
      print 'cycle: ',cycle
      t0=time.time()
      if evtR:
        evtR.clear()
      if rawCmd:
        self.__daq.begin(events=events_per_point)
        tb=time.time()
        self.__daq.end()
        te=time.time()
      else:
        self.begin(events=events_per_point)
        tb=time.time()
        self.wait()
        te=time.time()
      tneeded = time.time()-t0
      if evtR:
        mean_evtR = evtR.get()['mean']
        if mean_evtR is not np.nan:
          cycleMidTimes.append(evtR.get()['mean'])
      cycleBeginTimes.append(tb-t0)
      cycleWaitTimes.append(te-tb)
      #print "Daq.calibcycle: time needed till t0-begin %f" % (tb-ts)
      #print "Daq.calibcycle: time needed till begin-end %f" % (te-tb)
    runn = "#   run number (0 = not saved): %d\n" % self.runnumber()
    print runn
    #print 'time beg: ',cycleBeginTimes
    #print 'time wait: ',cycleWaitTimes
    diffTimes = [ cycleMidTimes[i]-cycleMidTimes[i-1] for i in range(1,len(cycleMidTimes)) ]
    print 'time differences: ',diffTimes
    print 'average time between mid-Scan: ',np.array(diffTimes).mean(),' beg: ',np.array(cycleBeginTimes).mean(),' wait ',np.array(cycleWaitTimes).mean()
    self.disconnect()
    print " ... done"

######################################################################
    
class EpicsFeedback(object):
  def __init__(self,feedbackPVs):
    """
    feedbackPVs is a dictionary of the form:
    "field_name" : ("PV:NAME", default_value)
    """
    self.feedbackPVs = feedbackPVs
    self.available = None
  
  def connect(self):
    if self.available is None:
      self.available = dict()
    for field, (pvname, _) in self.feedbackPVs.iteritems():
      try: 
        pv = Pv.add_pv_to_cache(pvname)
        if not pv.isconnected:
          pv.connect(1)
        self.available[field] = True
      except:
        print "did not find PV {}".format(self.feedbackPVs[field][0]) 
        self.available[field] = False

  def writeField(self,field,value):
    if not field in self.feedbackPVs.keys():
      return
    if self.available==None:
      self.connect()
    if self.available[field]:
      Pv.put(self.feedbackPVs[field][0],value)

  def cleanFields(self):
    for field, (pvname, default) in self.feedbackPVs.iteritems():
      self.writeField(field, default)

class EpicsFeedbackContext(object):
  def __init__(self, feedback):
    self.feedback = feedback

  def __enter__(self):
    self.feedback.connect()

  def __exit__(self, type, value, traceback):
    self.feedback.cleanFields()
