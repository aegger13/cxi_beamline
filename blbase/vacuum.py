import psp.Pv as Pv
from blutil import estr
from blutil.pypslog import logprint

class Valve:
  """ 
  Valve class : Used to control and monitor valves
  Instances defined in <hutch>/beamline.py
  This is for Pneumatic Gate Valves, only.
  See LeyboldValve derived class for electronic valves.
  """  
  def __init__(self,pvname,name):
    self.pvname = pvname
    self.name = name
    self._opn_sw = pvname + ":OPN_SW"    # command to control valve (1=open, 0=close)
    self._opn_di = pvname + ":OPN_DI"    # open-position readback
    self._cls_di = pvname + ":CLS_DI"    # close-position readback
    self._opn_ok = pvname + ":OPN_OK"    # ok to open? (interlock dependent)
                 
  def open(self):
    """ Opens a valve (sets OPN_SW to High) """
    Pv.put(self._opn_sw,1)
    
  def close(self):
    """ Closes a valve (sets OPN_SW to Low) """
    Pv.put(self._opn_sw,0)

  def isopen(self):
    """
    return true if the valve is open
    NB: A valve may be neither open or closed,
    or may be in an error state if both open and closed,
    these cases are not reported here    
    """
    return Pv.get(self._opn_di) == 1

  def isclosed(self):
    """
    return True if the valve is closed
    NB: A valve may be neither open or closed,
    or may be in an error state if both open and closed,
    these cases are not reported here    
    """
    return Pv.get(self._cls_di) == 1

  def openok(self):
    """  check wether valve is allowed to be open """
    return Pv.get(self._opn_ok)
    
  def status(self):
    """
    Returns the detailed status of a valve
    NB: If valve is neither open OR closed,
    or both open AND closed,
    status will be reported as 'NOT KNOWN'
    """
    op = self.isopen()
    cl = self.isclosed()
    if ((op and cl) or (not op and not cl)):
      vstatus=estr("NOT KNOWN", color='red',type='normal')     
    elif op:
      vstatus=estr("OPEN", color='green',type='normal')
    elif cl:
      vstatus=estr("CLOSED", color='orange',type='normal')
    str1 ="%s:" % self.name
    str2 =" %s" % vstatus
    str = str1.rjust(9)+str2.ljust(13)
    return str

  def __repr__(self):
    return self.status()


class LeyboldValve(Valve):
  """ Leybold Valve.
      These are not pneumatic, but electrical, usually small and on vent / purge lines.
      They don't have readback of their position, so when commanded open, they are open,
      otherwise closed
  """
  def __init__(self,pvname,name):
    Valve.__init__(self,pvname,name)
    self._opn_di=pvname + ":OPN_DO"  # use the digital output instead of the input which is not defined
    self._cls_di=None  # we override the logic to use opn_di instead
   
  def isclosed(self):
    """ returns True if valve is not commanded open """
    return Pv.get(self._opn_di) == 0
 

class Gauge:
  """ 
  Gauge class : Used to control and monitor gauges
  Instances defined in <hutch>/beamline.py
  """  
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__pmon=pvname + ":PMON"
    self.__enbl_sw=pvname + ":ENBL_SW"
    self.__statusmon=pvname + ":STATUSMON"
    self.__pstatsprbck=pvname + ":PSTATSPRBCK"  # PLC trip point readback value
    self.__pstatspdes=pvname + ":PSTATSPDES"  # PLC trip point set value

#  def on(self):
#    """ Turns a CC gauge on """
#    Pv.put(self.__enbl_sw,1)
    
#  def off(self):
#    """ Turns a CC gauge off """
#    Pv.put(self.__enbl_sw,0)

  def trip(self,value=None):
    """ Sets or Returns the gauge trip point for the vacuum PLC """
    previous_trip=Pv.get(self.__pstatsprbck)
    if (value is not None):
      Pv.put(self.__pstatspdes,value)
      s = "Resetting PLC trip point of `%s` from %.4g to %.4g" % (self.name,previous_trip,value)
      logprint(s,print_screen=True)
    else:
      print "%s trip point is %.4g" % (self.name,previous_trip)

  def pressure(self):
    """ Returns the pressure """
    return Pv.get(self.__pmon)

  def status(self):
    """ Returns the gauge reading """
    g_on = Pv.get(self.__statusmon)
    if (g_on !=0):
      gstatus=estr("Gauge Off",color='white',type='normal')
      str="%s: %s" % (self.name,gstatus)
    else:
      pressure=Pv.get(self.__pmon)
      if pressure<5e-8:
        gstatus=estr("%.1e Torr" % pressure ,color='green',type='normal')
      elif pressure<1e-6:
        gstatus=estr("%.1e Torr" % pressure ,color='orange',type='normal')
      else:
        gstatus=estr("%.1e Torr" % pressure ,color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % gstatus 
    str = str1.rjust(12)+str2.ljust(13)
    return str

  def __repr__(self):
    return self.status()


class IonPump:
  """ 
  IonPump class : Used to control and monitor IonPumps
  Instances defined in <hutch>/beamline.py
  """  
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__pmon=pvname + ":PMON" # Pressure in Torr
    self.__imon=pvname + ":IMON" # Current in Amps
    self.__vmon=pvname + ":VMON" # Voltage
    self.__statedes=pvname + ":STATEDES" # on/off control 
    self.__statemon=pvname + ":STATEMON" 
    self.__status=pvname + ":STATUS"
    self.__statuscode=pvname + ":STATUSCODE"
    self.__pumpsize=pvname + ":PUMPSIZE"
    self.__vpcname=pvname + ":VPCNAME" # controller running pump

  def on(self):
    """ Turns a Ion Pump on """
    Pv.put(self.__statedes,1)
    
  def off(self):
    """ Turns a Ion Pump off """
    Pv.put(self.__statedes,0)
  
  def status(self):
    """ Returns the ion pump pressure reading """
    p_on = Pv.get(self.__statemon)
    if (p_on ==0):
      pstatus=estr("Ion Pump Off",color='white',type='normal')
    else:
      pressure=Pv.get(self.__pmon)
      if pressure<5e-8:
        pstatus=estr("%.2e Torr" % pressure ,color='green',type='normal')
      elif pressure<1e-6:
        pstatus=estr("%.2e Torr" % pressure ,color='orange',type='normal')
      else:
        pstatus=estr("%.2e Torr" % pressure ,color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % pstatus 
    str = str1.rjust(8)+str2.ljust(16)
    return str

  def __repr__(self):
    return self.status()

  def info(self):
    """ Returns the ion pump information """
    current = Pv.get(self.__imon)
    voltage = Pv.get(self.__vmon)
    controller = Pv.get(self.__vpcname)
    pumpsize = Pv.get(self.__pumpsize)
    statemon = Pv.get(self.__statemon)
    if (statemon ==0):
      state=estr("Off",color='red',type='normal')
    elif (statemon ==1):
      state="On"
    else:
      state=estr("Unknown",color='white',type='normal')
    str="   %s\n" % (self.status())
    str += "   Current: %.2e Amps\n" % current
    str += "   Voltage: %4.0f Volts\n" % voltage
    str += "     State: %s\n" % state
    str += "      Size: %s l/s\n" % pumpsize
    str += "Controller: %s\n" % controller
    print str

class EbaraPump:
  """ class to control Ebara pumps """

  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__start=pvname + ":MPSTART_SW" # runstop button

  def run(self):
    """ starts the pump """
    Pv.put(self.__start,1)

  def stop(self):
    Pv.put(self.__start,0)

class TurboPump:
  """ class to control turbo pumps """

  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__start=pvname + ":START_SW" # runstop button

  def run(self):
    """ starts the pump """
    Pv.put(self.__start,1)

  def stop(self):
    Pv.put(self.__start,0)
