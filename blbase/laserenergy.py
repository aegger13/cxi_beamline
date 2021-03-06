import pyca
import psp.Pv as Pv
import pylab as pl
from blutil import estr
from blutil.calc import * 
from time import sleep
import numpy as np
class LaserEnergy:

  def __init__(self,name,wp_motor,wp_pv,user_pv=None,shg=0,leakage_pv=None,E0_pv=None):
    self.name = name
    self.wp_pv = wp_pv
    self.user_pv = user_pv
    self.leakage_pv = leakage_pv
    self.E0_pv = E0_pv
    self.wp_motor = wp_motor
    self.shg = shg
   
  def status(self):
    E=self.getE()
    E0=self.get_E0()
    leakage=self.get_leakage()
    wp=Pv.get(self.wp_pv)
    if self.shg:
      state=estr("400 nm",color='blue',type='normal')
    else:
      state=estr("800 nm",color='red',type='normal')
    str ="  %s: %4.4f\n" % (self.name,E)
    str +="      State: %s\n" % state
    str +="  Waveplate: %3.2f deg\n" % wp
    str +="         E0: %3.4f \n" % E0
    str +="    Leakage: %3.4f \n" % leakage
    return str

  def set(self,E):
    """ Sets the laser energy
        E is the desired laser energy (in either Joules or nomralized units
    """
    leakage=self.get_leakage()
    E0=self.get_E0()
    if E<leakage:
      str="Warning: desired value %3.4f is less than %3.4f leakage, setting wp to 0" % (E,leakage)
      self.wp_motor(0)
      E=self.getE()
      sleep(0.1)
      self.set_pv()
      print str
      return 
    if E>E0:
      str="Warning: desired value %3.4f is greater than the %3.4f availible energy, aborting" % (E,E0)
      print str
      return
    if self.shg:
      theta=0.5*asind(((E-leakage)/(E0-leakage))**0.25)
      self.wp_motor(theta)
      sleep(0.1)
      self.set_pv() 
      return
    else:
      theta=.5*asind(((E-leakage)/(E0-leakage))**0.5)
      self.wp_motor(theta)
      sleep(0.1)
      self.set_pv() 
      return

  def __repr__(self):
    return self.status()
  
  def __call_(self,value):
    """ Shortcut for setting the E, for example: laserE(0.5) """
    self.set(value)

  def get_leakage(self):
    """ Returns the leakage value """
    return Pv.get(self.leakage_pv)

  def set_leakage(self,leakage):
    """ Sets the leakage value """
    Pv.put(self.leakage_pv,leakage)
    sleep(0.1)
    self.set_pv()
    return 
 
  def get_E0(self):
    """ Returns the E0 value """
    return Pv.get(self.E0_pv)

  def set_E0(self,E0):
    """ Sets the E0 value """
    Pv.put(self.E0_pv,E0)
    sleep(0.1)
    self.set_pv()
    return 
 
  def set_pv(self):
    if self.user_pv==None:
      return
    E=self.getE()
    Pv.put(self.user_pv,E)
    return
    
  def getE(self):
    #wp=Pv.get(self.wp_pv)
    wp=self.wp_motor.wm()
    E0=self.get_E0()
    leakage=self.get_leakage()
    if self.shg:
      E=(E0-leakage)*(sind(2*wp))**4+leakage
      return E
    else:
      E=(E0-leakage)*(sind(2*wp))**2+leakage
      return E
  def getEval(self,wp):
    E0=self.get_E0()
    leakage=self.get_leakage()
    if self.shg:
      E=(E0-leakage)*(sind(2*wp))**4+leakage
      return E
    else:
      E=(E0-leakage)*(sind(2*wp))**2+leakage
      return E
 
###################################

class LaserEnergyPolarizer:

  def __init__(self,name,wp_motor,wp_pv,user_pv=None,leakage_pv=None,E0_pv=None):
    self.name = name
    self.wp_pv = wp_pv
    self.user_pv = user_pv
    self.leakage_pv = leakage_pv
    self.E0_pv = E0_pv
    self.wp_motor = wp_motor
    self.shg = shg
   
  def status(self):
    E=self.getE()
    E0=self.get_E0()
    leakage=self.get_leakage()
    wp=Pv.get(self.wp_pv)
    str ="  %s: %4.4f\n" % (self.name,E)
    str +="      State: %s\n" % state
    str +="  Waveplate: %3.2f deg\n" % wp
    str +="         E0: %3.4f \n" % E0
    str +="    Leakage: %3.4f \n" % leakage
    return str

  def set(self,E):
    """ Sets the laser energy
        E is the desired laser energy (in either Joules or nomralized units
    """
    leakage=self.get_leakage()
    E0=self.get_E0()
    if E<leakage:
      str="Warning: desiried value %3.4f is less than %3.4f leakage, setting wp to 0" % (E,leakage)
      self.wp_motor(0)
      E=self.getE()
      sleep(0.1)
      self.set_pv()
      print str
      return 
    if E>E0:
      str="Warning: desiried value %3.4f is greater than the %3.4f availible energy, aborting" % (E,E0)
      print str
      return
    theta=1*asind(((E-leakage)/(E0-leakage))**0.5)
    self.wp_motor(theta)
    sleep(0.1)
    self.set_pv() 
    return

  def __repr__(self):
    return self.status()
  
  def __call_(self,value):
    """ Shortcut for setting the E, for example: laserE(0.5) """
    self.set(value)

  def get_leakage(self):
    """ Returns the leakage value """
    return Pv.get(self.leakage_pv)

  def set_leakage(self,leakage):
    """ Sets the leakage value """
    Pv.put(self.leakage_pv,leakage)
    sleep(0.1)
    self.set_pv()
    return 
 
  def get_E0(self):
    """ Returns the E0 value """
    return Pv.get(self.E0_pv)

  def set_E0(self,E0):
    """ Sets the E0 value """
    Pv.put(self.E0_pv,E0)
    sleep(0.1)
    self.set_pv()
    return 
 
  def set_pv(self):
    if self.user_pv==None:
      return
    E=self.getE()
    Pv.put(self.user_pv,E)
    return
    
  def getE(self):
    wp=Pv.get(self.wp_pv)
    E0=self.get_E0()
    leakage=self.get_leakage()
    E=(E0-leakage)*(sind(wp))**2+leakage
    return E
    
###################################

class calibWP(object):
  def __init__(self, wp_motor, calib_file=None, motCol=0, eCol=1):
    self.wp_motor = wp_motor
    self.showPlot = False
    self.__havePlot = False
    self.calib_file = calib_file
    if self.calib_file:
      d = np.loadtxt(calib_file)
      srt = d[:,motCol].argsort()
      self._dat_wp=d[srt,motCol]
      self._dat_Esam = d[srt,eCol]
    else:      
      self._dat_wp=[]
      self._dat_Esam=[]

  def _haveCalib(self):
    if len(self._dat_wp)<2:
      print 'we are missing a calibration file to use'
      fname = raw_input('We are missing a calibration file to use, please enter one')
      try:
        d = np.loadtxt(fname)
        srt = d[:,motCol].argsort()
        self._dat_wp=d[srt,motCol]
        self._dat_Esam = d[srt,eCol]
        self.calib_file = fname
      except:
        return False
    return True

  def plot(self):
    if not self._haveCalib():
      return
    pl.figure(100)
    pl.plot(self._dat_wp,self._dat_Esam,'k-o')
    pl.xlabel('las_opa_wp')
    pl.ylabel('Pulse energy / $\mu$J')
    self.__havePlot = True

  def getPosWP(self, Edes):
    if not self._haveCalib():
      return None
    wpvalue = np.nan
    if Edes>np.max(self._dat_Esam) or Edes<np.min(self._dat_Esam):
      print 'Not in accessible WP range!'
      print 'range is from %g to %g' %(np.min(self._dat_Esam),np.max(self._dat_Esam))
    else:
      wpvalue = np.interp(Edes,self._dat_Esam,self._dat_wp)
      if self.showPlot:
        if not self.__havePlot:
          self.plot()
        pl.axvline(wpvalue)
        pl.axhline(Edes)
    return wpvalue

  def getPosE(self, WPdes):
    if not self._haveCalib():
      return None
    Evalue = np.nan
    if WPdes>np.max(self._dat_wp) or WPdes<np.min(self._dat_wp):
      print 'Not in accessible WP range!'
      print 'range is from %g to %g' %(np.min(self._dat_wp),np.max(self._dat_wp))
    else:
      Evalue = np.interp(WPdes,self._dat_wp,self._dat_Esam)
      if self.showPlot:
        if not self.__havePlot:
          self.plot()
        pl.axvline(Evalue)
        pl.axhline(WPdes)
    return Evalue

  def _moveE(self, Edes):
    wpPos = self.getPosWP(Edes)
    if wpPos:
      self.wp_motor.mv(wpPos)

  def _getE(self):
    wpPos = self.wp_motor.wm() 
    return self.getPosE(wpPos)

  def _waitE(self, Edes):
    wp_motor.wait()
