import time
import blutil
from psp import Pv
from blbase.stateioc import stateiocDevice
from functools import partial
import numpy as np
import blutil.config as config
from blutil.edm import edm_hutch_open

class PulsePicker(object):
  """beamrate only needed for automatic delay for pulsing"""


  def __init__(self,evr,lcls,sequencer,polarity,xstage,ystage,rotPVbase,presetPVbase,codes,burstdelay=4.5e-3,flipflopdelay=8e-3,followerdelay=3.8e-5):
    self.x = xstage
    self.y = ystage
    self._rotPVbase = rotPVbase
    self.trigger = evr
    self._lcls = lcls
    self._seq = sequencer
    self._codes = codes
    self._burstdelay = burstdelay
    self._flipflopdelay = flipflopdelay
    self._followerdelay = followerdelay
    self._yPreset = stateiocDevice('%s:Y'%presetPVbase)
    for preset in self._yPreset.statesAll():
      self.__dict__['mv_'+preset] = partial(self._move_to_preset,preset)

  def _move_to_preset(self,preset):
    self._cleanup()
    self.x.mv(0)
    self._yPreset.move(preset)

  def _PVname(self,fieldname):
    return self._rotPVbase + ':' + fieldname

  def home(self):
    """ home the pulse picker rotation motor """
    self._cleanup()
    Pv.put(self._PVname('HOME:MOTOR'),1)
    Pv.wait_until_change(self._PVname('SE'),1)
    Pv.wait_for_value(self._PVname('SE'),0)

  def flipflop(self):
    """ puts the pulse picker in flip-flop mode """
    self._cleanup()
    self.trigger.delay(self._flipflopdelay)
    Pv.put(self._PVname('RUN_FLIPFLOP'),1)
    Pv.wait_for_value(self._PVname('SE'),2)

  def burst(self):
    """ puts the pulse picker in burst mode """
    self._cleanup()
    self.trigger.delay(self._burstdelay)
    Pv.put(self._PVname('RUN_BURSTMODE'),1)
    Pv.wait_for_value(self._PVname('SE'),3)

  def follower(self):
    """ puts the pulse picker in follower mode """
    self._cleanup()
    self.trigger.delay(self._followerdelay)
    Pv.put(self._PVname('RUN_FOLLOWERMODE'),1)
    Pv.wait_for_value(self._PVname('SE'),6)

  def get_motor_status(self):
    pass

  def edm_control(self):
    edm_hutch_open("pp_screens/pp_mode_control.edl", MOTOR=self._rotPVbase)

  def status(self):
    #get clostest position in y
    #deltas = self.y._presetDelta()
    status = ''
    status += 'Pulse picker -- '
    isopen = Pv.get(self._PVname('DF'))==0
    if isopen:
      status += blutil.estr('open',color='green')+'\n'
    else:
      status += blutil.estr('closed',color='red')+'\n'
    #status += '\t%g from %s' %(deltas[0][1],deltas[0][0])
    #status += '\n'
    #status += self.trigger.status()

    return status

  def __repr__(self):
    return self.status()

  #def reset(self):
    #self.evr.setDefaults()

  def open(self,fast=False):
    """ open the shutter; the option fast when enable skip the test
    that makes sure that the output is not triggered by any event code"""
    #if (not fast):
      #self.evr.disableAllEvents()
    #self.evr.polarity(self.__polarity);
    self._cleanup()
    Pv.put(self._PVname('S_OPEN'),1)
    
  def close(self,fast=False):
    """ close the shutter; the option fast when enable skip the test
    that makes sure that the output is not triggered by any event code"""
    #if (not fast):
      #self.evr.disableAllEvents()
    #self.evr.polarity(not self.__polarity)
    self._cleanup()
    Pv.put(self._PVname('S_CLOSE'),1)
  
  def _cleanup(self):
    self._seq.stop()
    self._reset_mode()
    Pv.wait_for_value(self._PVname("SD_L"),0)
    # wait after this cleanup finishes - causes some issues otherwise
    time.sleep(0.5)

  def _reset_mode(self):
    Pv.put(self._PVname('RESET_PG'),1)

  def set_mode(self,Nshots):
    if Nshots == 1:
      self.flipflop()
    elif Nshots>1:
      self.burst()
    
  def prepare_burst(self,Nshots,Nbursts=1,freq=120,delay=None,burstMode=False,setReadoutTrig=False,readoutCode=None):
    self.set_mode(Nshots)

    beamrate = self._lcls.get_xraybeamrate()
    self._set_Nbursts(Nbursts)
    if setReadoutTrig:
      if readoutCode is None:
        self._codes['readout'] = self._codes['slowdaq']
      else:
        self._codes['readout'] = readoutCode

    # set up burst mode values
    if burstMode:
      burst = Nshots + 2
    else:
      burst = 0

    if not freq==120:
      raise(NotImplementedError('Not implemented yet!'))
    if Nshots == 1:
      if delay is None:
        delay = 3
      elif delay < 2:
        raise ValueError('Delay between flip flops of less than two is not allowed')
      seqstep = 0
      self._seq.setstep(seqstep,self._codes['pp'],delay,fiducial=0,burst=burst,comment='PulsePicker');seqstep+=1
      self._seq.setstep(seqstep,self._codes['drop'],0,fiducial=0,comment='OffEvent');seqstep+=1
      self._seq.setstep(seqstep,self._codes['daq'],2,fiducial=0,comment='OnEvent');seqstep+=1
      if setReadoutTrig:
        self._seq.setstep(seqstep,self._codes['readout'],0,fiducial=0,comment='readout');seqstep+=1

    elif Nshots>1:
      if delay is None:
        delay = 1
      elif delay < 1:
        raise ValueError('Delay between bursts of less than one is not allowed')
      seqstep = 0
      self._seq.setstep(seqstep,self._codes['pp'],delay,fiducial=0,burst=burst,comment='PulsePicker');seqstep+=1
      self._seq.setstep(seqstep,self._codes['drop'],0,fiducial=0,comment='OffEvent');seqstep+=1
      self._seq.setstep(seqstep,self._codes['drop'],1,fiducial=0,comment='OffEvent');seqstep+=1
      for shotNo in range(Nshots):
        self._seq.setstep(seqstep,self._codes['daq'],1,fiducial=0,comment='OnEvent');seqstep+=1
        if shotNo==Nshots-2:
          self._seq.setstep(seqstep,self._codes['pp'],0,fiducial=0,comment='PulsePicker');seqstep+=1
        if setReadoutTrig and shotNo==Nshots-1:
          self._seq.setstep(seqstep,self._codes['readout'],0,fiducial=0,comment='readout');seqstep+=1
    self._seq.setnsteps(seqstep)
    self._seq.update()

  def _set_Nbursts(self,Nbursts):
    if Nbursts==1:
      self._seq.modeOnce()
    elif Nbursts>1:
      self._seq.modeNtimes(N=Nbursts)
    elif Nbursts<0:
      self._seq.modeForever()

  def get_burst(self,N=None):
    if not N==None:
      self._set_Nbursts(N)
    self._seq.start()

  def stop_burst(self):
    self._seq.stop()


### Miller Experiment specific modes - could be generally applicable for similar experiments ###

  def setSeqBurst(self, Nshots,readSlow=False):
    self.burst()
    seqstep = 0
    self._seq.setstep(seqstep,self._codes['pp'],1,fiducial=0,comment='PulsePicker');seqstep+=1
    self._seq.setstep(seqstep,self._codes['drop'],0,fiducial=0,comment='OffEvent');seqstep+=1
    self._seq.setstep(seqstep,self._codes['drop'],1,fiducial=0,comment='OffEvent');seqstep+=1
    for shotNo in range(Nshots):
      self._seq.setstep(seqstep,self._codes['daq'],1,fiducial=0,comment='OnEvent');seqstep+=1
      if shotNo==Nshots-2:
        self._seq.setstep(seqstep,self._codes['pp'],0,fiducial=0,comment='PulsePicker');seqstep+=1
    if readSlow:
      self._seq.setstep(seqstep,self._codes['slowdaq'],0,fiducial=0,comment='OnEventRayonix');seqstep+=1
    self._seq.setnsteps(seqstep)
    self._seq.update()

  def setSeqBurstSingle(self, readSlow=False, nShots=1, skipShot=4):
    self.burst()
    seqstep = 0
    for iS in range(nShots):
      self._seq.setstep(seqstep,self._codes['ppsingleopen'],1,fiducial=0,comment='PulsePickerOpen');seqstep+=1
      self._seq.setstep(seqstep,self._codes['drop'],0,fiducial=0,comment='OffEvent');seqstep+=1
      self._seq.setstep(seqstep,self._codes['lshut'],0,fiducial=0,comment='LaserShutter');seqstep+=1
      #the second OffEvent, where we'll open the laser shutter.
      self._seq.setstep(seqstep,self._codes['drop'],1,fiducial=0,comment='OffEvent');seqstep+=1
      #self._seq.setstep(seqstep,self._codes['lshut'],0,fiducial=0,comment='LaserShutter');seqstep+=1
      #now our OnEvent where we'll also sloce the pulse picker.
      self._seq.setstep(seqstep,self._codes['daq'],1,fiducial=0,comment='OnEvent');seqstep+=1
      if readSlow:
        self._seq.setstep(seqstep,self._codes['slowdaq'],0,fiducial=0,comment='OnEventRayonix');seqstep+=1
        self._seq.setstep(seqstep,self._codes['singleshotana'],0,fiducial=0,comment='SingleShotEvt');seqstep+=1
      self._seq.setstep(seqstep,self._codes['ppsingleclose'],0,fiducial=0,comment='PulsePickerClose');seqstep+=1
      if nShots > 0 and iS < (nShots-1):
        self._seq.setstep(seqstep,self._codes['drop'],skipShot,fiducial=0,comment='OffEvent');seqstep+=1

    self._seq.setnsteps(seqstep)
    self._seq.update()

  def prepare_FlipFlop(self,Nshots, prePP=3, aggressive=False,setReadoutTrig=False,readoutCode=None):
    if setReadoutTrig:
      if readoutCode is None:
        self._codes['readout'] = self._codes['slowdaq']
      else:
        self._codes['readout'] = readoutCode
    self.flipflop()
    self.trigger.width(1e-4)
    if aggressive:
      self.trigger.delay(8e-7)

    seqstep = 0
    for shotNo in range(Nshots):
      pptrig = np.copy(seqstep)
      self._seq.setstep(seqstep,self._codes['pp'],prePP,fiducial=0,comment='PulsePicker');seqstep+=1
      self._seq.setstep(seqstep,self._codes['drop'],0,fiducial=0,comment='OffEvent');seqstep+=1
      self._seq.setstep(seqstep,self._codes['daq'],2,fiducial=0,comment='OnEvent');seqstep+=1
      if setReadoutTrig:
        self._seq.setstep(seqstep,self._codes['readout'],0,fiducial=0,comment='readout');seqstep+=1
    self._seq.setnsteps(seqstep)
    self._seq.update()
