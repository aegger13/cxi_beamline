# ipimb class from xpp's lusiipm.py file
# this is used extensively in xppbeamline

import os
import subprocess
from blutil import estr
from blbase import virtualmotor
import psp.Pv as Pv

class ipimb:
  """ Class to define gain position and other ipimb parameters (timing)
  """
  _gain_enum_states = ["1pF", "4.7pF", "24pF", "120pF", "620pF",
                       "3.3nF", "10nF", "5.7pF", "28.7pF", "144pF",
                       "740pF", "3.92nF", "13.3nF", "0pF", "14nF"]

  def __init__ (self, basePV, iocPV, evrPV, desc='ipimb'):
    self.basePV = basePV
    self.__iocPV = iocPV
    self.__evrPV = evrPV
    self.__evrBase = evrPV.split(":CTRL")[0]
    self.__delayPV  = basePV+':TrigDelay'
    self.__gainPV = basePV+':ChargeAmpRangeCH'
    self.__biasPV  = basePV+':DiodeBias'
    self.__minGain = 0
    self.__maxGain = len(self._gain_enum_states)
    self.__minDelay = 0
    self.__maxDelay = 1e6
    self.__minBias = 0
    self.__maxBias = 100
    self.__desc=desc
    self.dconfpv = Pv.Pv(self.__evrPV)
    self.dconfpv.config = False
    self.delay = virtualmotor.VirtualMotor(self.desc()+'_delay',self.__setDelay,self.__getDelay,self.__waitConfig)
    self.gain = virtualmotor.VirtualMotor(self.desc()+'_gain',self.setGain,self.getGain,self.__waitConfig)
    self.bias = virtualmotor.VirtualMotor(self.desc()+'_bias',self.__setBias,self.__getBias,self.__waitConfigBias)

  def getFEXpars(self):
    #str  = estr("%s" % self.__desc,color="black",type="bold")
    str = " Fex Base(0/4) = (%.4f %.4f% .4f %.4f), " % (Pv.get(self.basePV+":CH0_BASE"),Pv.get(self.basePV+":CH1_BASE"),Pv.get(self.basePV+":CH2_BASE"),Pv.get(self.basePV+":CH3_BASE"))
    str += " Fex Scale(0/4) = (%.4f %.4f% .4f %.4f), " % (Pv.get(self.basePV+":CH0_SCALE"),Pv.get(self.basePV+":CH1_SCALE"),Pv.get(self.basePV+":CH2_SCALE"),Pv.get(self.basePV+":CH3_SCALE"))
    return str

  def getConfigpars(self):
    #str  = estr("%s" % self.__desc,color="black",type="bold")
    str = " Trigger delay = %.4f, " % (Pv.get(self.__delayPV))
    str += " Gain (0/4) = (%.4f %.4f% .4f %.4f), " % (Pv.get(self.__gainPV+"0"),Pv.get(self.__gainPV+"1"),Pv.get(self.__gainPV+"2"),Pv.get(self.__gainPV+"3"))
    return str

  def status(self):
    str  = estr("%s" % self.__desc,color="black",type="bold")
    str += " %s" % self.getConfigpars()
    str += " %s" % self.getFEXpars()
    return str

  def desc(self):
    return self.__desc

  def __waitCondition(self):
    if self.dconfpv.value == 1:
      v = self.dconfpv.config
      self.dconfpv.config = False
      if v:
        return True
    else:
      self.dconfpv.config = True
    return False

  def __waitConfig(self, timeout=5):
    print 'waitconfig, timeout: ',timeout
    self.dconfpv.wait_condition(1, self.__waitCondition, timeout=timeout)

  def __waitConfigBias():
    print 'waitconfigBias, timeout will be 15'
    self.waitConfig(timeout=15)

  def __getDelay(self):
    return Pv.get(self.__delayPV)

  def __setDelay(self, delay):
    if (delay > self.__maxDelay or delay < self.__minDelay):
      print ' the requested delay has to be between %s and %s'%(self.__minDelay, self.__maxDelay)
      print ' leave delay at ',self.__getDelay
      return
    Pv.put(self.__delayPV, delay)

  def __getBias(self):
    return Pv.get(self.__biasPV)

  def __setBias(self, bias):
    #fix this, unprotexted now
    if (bias > self.__maxBias or bias < self.__minBias):
      print ' the requested bias has to be between %s and %s'%(self.__minBias, self.__maxBias)
      print ' leave bias at ', self.__getBias()
      return
    Pv.put(self.__biasPV, bias)

  def __setGainN(self, igain, num):
    """
    Set ipimb gain as an integer index in the enum.

    Return True if args were ok, False otherwise.
    """
    if (not isinstance(num, int)):
      print 'channel number should be an integer!'
      return False
    currgain = self.__getGainN(num)
    if currgain is None:
      return False
    if (igain == -1):
      igain = currgain-1
    elif (igain == 101):
      igain = currgain+1
    if igain < self.__minGain:
      igain = self.__minGain
    elif igain >= self.__maxGain:
      igain = self.__maxGain - 1
    if 0 <= num <= 3:
      gain_str = self.__gainPV+str(num)
    else:
      print 'invalid channel # %f, wont set gain' %num
      return False
    Pv.put(gain_str, igain)
    return True

  def setGain(self, gain, num=-1):
    """
    Set ipimb gain.

    Parameters:
    gain: string gain value, one of the following options:
         ["1pF", "4.7pF", "24pF", "120pF", "620pF",
          "3.3nF", "10nF", "5.7pF", "28.7pF", "144pF",
          "740pF", "3.92nF", "13.3nF", "0pF", "14nF"]
    you can also use "+1" to go to the next option on the list,
    or "-1" to go to the previous option.
    num: integer, which channel to set. Leave at -1 to set all.
    """
    if num == -1:
      for i in range(4):
        ok = self.setGain(gain, i)
        if not ok:
          return False
      return True
    else:
      if gain in ("+1", 1):
        igain = 101
      elif gain in ("-1", -1):
        igain = -1
      else:
        try:
          igain = self._gain_enum_states.index(gain)
        except:
          print "Invalid gain string. Your options are:"
          for opt in self._gain_enum_states:
            print opt
          print "You can also use '+1' or '-1' to switch to the next or previous option in the enum list."
          return False
      return self.__setGainN(igain, num)

  def __getGainN(self, num):
    """
    Get ipimb gain as an integer index in the enum, or None on invalid arg.
    """
    if (not isinstance(num, int)):
      print 'channel number should be an integer!'
      return
    if 0 <= num <= 3:
      gain_str = self.__gainPV+str(num)
      return Pv.get(gain_str)
    else:
      print 'invalid channel # %f, wont get gain' %num
      return

  def getGain(self, num=-1):
    """
    Get ipimb gain.

    Parameters:
    num: integer channel number. Leave at -1 to get all channels.
    """
    if num == -1:
        gains = [self.getGain(i) for i in range(4)]
        if None in gains:
            return
        return gains
    else:
        enum_val = self.__getGainN(num)
        if enum_val is None:
            return
        return self._gain_enum_states[enum_val]

  def config_gui(self):
    """
    Open the ipimb gain setting gui.
    """
    cwd = "/reg/g/pcds/controls/pycaqt/ipimb"
    DEVNULL = open(os.devnull, "w")
    subprocess.Popen(("./ipimbtool",
        "--base", self.basePV,
        "--ioc", self.__iocPV,
        "--evr", self.__evrBase,
        "--dir", cwd),
        cwd=cwd,
        stdout=DEVNULL,
        stderr=subprocess.STDOUT
        )
