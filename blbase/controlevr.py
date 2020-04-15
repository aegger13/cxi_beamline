import time
from psp import Pv
from virtualmotor import VirtualMotor


class EVRTrigger(object):
  def __init__(self, ioc, trigger=0, name="EVR Trigger"):
    """ 32 bit delay and width
        15 bit prescaler """
    self.name=name
    self.ioc=ioc
    self.nevent_numbers = 14
    self.trigger = trigger
    self.pvnames = self.__getpvnames()
    self.__evr_clock = 119e6
    m1name = "%s:trigger%s.delay" % (name,trigger)
    self.delayMotor = VirtualMotor(m1name,self.delay,self.delay)
    m1name = "%s:trigger%s.width" % (name,trigger)
    self.widthMotor= VirtualMotor(m1name,self.width,self.width)

  def __getpvnames(self):
    ret = dict()
    for i in range(1,self.nevent_numbers+1):
      ret[i] = dict()
    t = hex(self.trigger)[-1].capitalize()
    for event in range(1,self.nevent_numbers+1):
      ret[event]["enable"]    = self.ioc + ":EVENT%dCTRL.ENAB" % event
      ret[event]["eventcode"] = self.ioc + ":EVENT%dCTRL.ENM" % event
      ret[event]["eventcodename"] = self.ioc + ":EVENT%d_NAME" % event
      ret[event]["triggerenabled"] = self.ioc + ":EVENT%dCTRL.OUT%s" % (event,t)
      ret[event]["irq"] = self.ioc + ":EVENT%dCTRL.VME" % event
      ret[event]["count"] = self.ioc + ":EVENT%dCNT" % event
      ret[event]["clock"] = self.ioc + ":EVENT%dRATE" % event

    ret["polarity"] = self.ioc+":TRIG%s:TPOL" % t
    ret["width"] = self.ioc+":TRIG%s:TWID" % t
    ret["delay"] = self.ioc+":TRIG%s:TDES" % t
    ret["delay_ticks_rb"] = self.ioc+":TRIG%s:BW_TDLY" % t
    ret["width_ticks_rb"] = self.ioc+":TRIG%s:BW_TWID_TICKS" % t
    ret["width_rb"] = self.ioc+":TRIG%s:BW_TWIDCALC" % t
    ret["delay_rb"] = self.ioc+":TRIG%s:BW_TDES" % t
    ret["enable"] = self.ioc+":TRIG%s:TCTL" % t
    ret["eventcode"] = self.ioc+":TRIG%s:TEC" % t
    ret["eventcode_rb"] = self.ioc+":TRIG%s:EC_RBV" % t
    return ret

  def isEnable(self):
    pvs = self.pvnames
    return Pv.get(pvs["enable"])

  def enable(self):
    pvs = self.pvnames
    return Pv.put(pvs["enable"],1)

  def disable(self):
    pvs = self.pvnames
    return Pv.put(pvs["enable"],0)

  def eventcode(self,eventcode=None):
    if (eventcode is not None):
      pv=self.pvnames["eventcode"]
      return Pv.put(pv,eventcode)
    else:
      pv=self.pvnames["eventcode_rb"]
      return  Pv.get(pv)

  def clock(self,clock=None):
    if (clock is None):
      return self.__evr_clock/self.prescale()
    else:
      p=round(self.__evr_clock/clock)
      return self.prescale(p)

  def polarity(self,P=None):
    if ("polarity" not in self.pvnames):
      return 0
    pv=self.pvnames["polarity"]
    if (P is None):
      return Pv.get(pv)
    else:
      return Pv.put(pv,int(P))

  def prescale(self,v=None):
    if ("prescale" not in self.pvnames):
      return 1
    pv=self.pvnames["prescale"]
    if (v is None):
      return Pv.get(pv)
    else:
      v=round(v)
      if (v>( (1<<15)-1 ) ):
        print "Requested value for prescale (%d) is outside range (0-%d)" % (v,(1<<15)-1)
      return Pv.put(pv,round(v))

  def delay(self,delay=None):
    if (delay is not None):
      pv=self.pvnames["delay"]
      return Pv.put(pv,delay*1e9)
    else:
      pv=self.pvnames["delay_rb"]
      return  Pv.get(pv)/1e9

  def delayTicks(self,delay=None):
    pv=self.pvnames["delay_ticks_rb"]
    if (delay is None):
      return Pv.get(pv)
    else:
      raise Exception('No tick setting pv available, use delay method instead!')

  def width(self,width=None):
    if (width is not None):
      pv=self.pvnames["width"]
      return Pv.put(pv,width*1e9)
    else:
      pv=self.pvnames["width_rb"]
      return  Pv.get(pv)/1e9
  
  def _getWidthSec(self):
    return self.width()[0]

  def widthTicks(self,width=None):
    pv=self.pvnames["width_ticks_rb"]
    if (width is None):
      return Pv.get(pv)
    else:
      raise Exception('No tick setting pv available, use delay method instead!')

  def status(self):
    str  = "IOC: %s (%s)\n"   % (self.ioc,self.name)
    str += " trigger  : %d\n" % self.trigger
    str += " enabled? : %s\n" % bool(self.isEnable())
    p = self.polarity();
    if (p==0):
      ps = "Normal"
    else:
      ps = "Inverted"
    str += " polarity : %s (= %d)\n" % (ps,p)
    str += " clock (freq,pres): %.7e,%d\n" % (self.clock(),self.prescale())
    d = self.width()
    dt = self.widthTicks()
    str += " width (sec,tics): %.7e,%d\n" % (d,dt)
    d = self.delay()
    dt = self.delayTicks()
    str += " delay (sec,tics): %.7e,%d\n" % (d,dt)
    ec = self.eventcode()
    str += " firing on event code: %d\n" % ec
    return str

  def __repr__(self):
    return self.status()


class ControlEVR(object):
  """ Control EVR
  32 bit delay and width
  15 bit prescaler
  119MHz clock"""
  def __init__(self, ioc, name="Control EVR"):
    self.name = name
    self.t0 = EVRTrigger(ioc,0,name)
    self.t1 = EVRTrigger(ioc,1,name)
    self.t2 = EVRTrigger(ioc,2,name)
    self.t3 = EVRTrigger(ioc,3,name)
    self.t4 = EVRTrigger(ioc,4,name)
    self.t5 = EVRTrigger(ioc,5,name)
    self.t6 = EVRTrigger(ioc,6,name)
    self.t7 = EVRTrigger(ioc,7,name)
    self.t8 = EVRTrigger(ioc,8,name)
    self.t9 = EVRTrigger(ioc,9,name)
    self.t10 = EVRTrigger(ioc,10,name)
    self.t11 = EVRTrigger(ioc,11,name)
    self.t12 = EVRTrigger(ioc,12,name)
    self.t13 = EVRTrigger(ioc,13,name)
    self.ioc = ioc


  def status(self,trigger=0):
    t = self.__getattribute__("t%d" % trigger)
    return t.status()

  def __call__(self,trigger=0):
    t = self.__getattribute__("t%d" % trigger)
    print t.status()

