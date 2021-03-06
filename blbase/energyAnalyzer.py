#!/usr/bin/python
# This module provides support 
# for the RIXS Energy Analyzer
# 
# Author:         Daniel Flath (SLAC), Roman Mankowsky (CFEL)
# Created:        Mar 21, 2013
# Modifications:
#   Apr 1, 2013 RM
#       version 2

import numpy as n
from numpy import rad2deg,arcsin,sqrt,tan
import sys
from blutil import estr
import psp.Pv as Pv
from blutil.pypslog import logprint
import math
from device import Device

class EnergyAnalyzer(Device):
  """
  Class to control the Si-Crystal Energy Analyzer

  Motors are:

  thC: analyzer Crystal motor theta
  tth: analyzer Detector motor 2theta

  Additionally, 1 virtual motor is defined:

  En: Moves thCrystal and tthetector in coordination to achieve a theta-2theta energy scan.
      See methods 'En*'
  """

  def __init__(self,ath,atth,anaz,detz,achi,yagzoom,yagfocus,diamondx,diamondy,objName="analyzer",pvBase=None):
    self.ath = ath
    self.atth = atth
    self.anaz = anaz
    self.detz = detz
    self.achi = achi
    self.yagzoom = yagzoom
    self.yagfocus = yagfocus
    self.diamondx = diamondx
    self.diamondy = diamondy
    self.objName = objName
    self.detCenOffset = None
    self.pvBase = pvBase
    self.llpv = None
    self.hlpv = None
    self.hkl = n.array( [8,4,4] )
     
    self.motors = {
      "ath":  ath,
      "atth": atth,
      "anaz": anaz,
      "detz": detz,
      "achi": achi,
      "yagzoom": yagzoom,
      "yagfocus": yagfocus,
      "diamondx": diamondx,
      "diamondy": diamondy
      }

    if self.pvBase is not None:
      self.llpv = self.pvBase+":ea_lowlim"
      self.hlpv = self.pvBase+":ea_highlim"
      pass

#  def status(self):
#    return Device(self).status() + "\nROI: %s" % (self.getDetROI())

  def setLatticeConst(self, val):
    if self.pvBase is not None:
      Pv.put(self.pvBase + ":Lattice_Const",val)
      pass
    pass

  def getLatticeConst(self):
    if self.pvBase is not None:
      return Pv.get(self.pvBase + ":Lattice_Const")
      pass
    pass


  def setDetROI(self,x1,y1,x2=None,y2=None):
    if x2 is None:
      x2 = x1
      pass
    if y2 is None:
      y2 = y1
      pass
    Pv.put(self.pvBase + ":det_roi_x1", x1)
    Pv.put(self.pvBase + ":det_roi_y1", y1)
    Pv.put(self.pvBase + ":det_roi_x2", x2)
    Pv.put(self.pvBase + ":det_roi_y2", y2)
    pass

  def getDetROI(self):
    return [int(Pv.get(self.pvBase + ":det_roi_x1")),
            int(Pv.get(self.pvBase + ":det_roi_y1")),
            int(Pv.get(self.pvBase + ":det_roi_x2")),
            int(Pv.get(self.pvBase + ":det_roi_y2"))
            ]
  

#Here come the definitions of the Virtual motor methods

  def assertLimitsEn(self, energy):
    """ Check that 'virtual motor' position is reachable by all physical stages """
    ll = self.getLowLimEn()
    if energy <= ll:
      print "%f is less than or equal to low limit of %f" % (energy,ll)
      return False
    hl = self.getHiLimEn()
    if energy >= hl:
      print "%f is more than or equal to hi limit of %f" % (energy,hl)
      return False
    #just check soft limits of motors as well
    th = self.convertEnergyToAngle(energy)
    if th <= self.ath.get_lowlim() or th >= self.ath.get_hilim() or ( 2 * th) <= self.atth.get_lowlim() or (2 * th) >= self.atth.get_hilim():
      print 'failed physical motor limits on ath or atth'
      return False
    return True

  def moveEn(self, energy):
    """ Move Energy to value -> Analyzer crystal to according theta, detector to 2theta """
    self.energy = energy
    th = self.convertEnergyToAngle(energy)
    if th is not None and self.assertLimitsEn(energy):
      print "moving th, tth to %f,%f" % (th,2 * th)
      self.ath.move_silent(th)
      self.atth.move_silent(2 * th)
      if self.pvBase is not None:
        #print "putting energy"
        Pv.put(self.pvBase + ":Analyzer_Energy",energy)
        pass
    pass

  def checkMoveEn(self, energy):
    """ Move Energy to value -> Analyzer crystal to according theta, detector to 2theta """
    self.energy = energy
    th = self.convertEnergyToAngle(energy)
    if th is not None and self.assertLimitsEn(energy):
      print "would move th, tth to %f,%f" % (th,2 * th)
    pass
    

  def wmEn(self):
    """ Retrieve position (energy) of En virtual motor calculated from ath physical stage""" 
    th = self.ath.wm()
    energyth = self.convertAngleToEnergy(th)
    return energyth
    pass
  
  def waitEn(self):
    """ Wait for movement completion of physical motors which comprise virtual motor En """
    self.ath.wait()
    self.atth.wait()
    pass

  def setLowLimEn(self,en):
    hltth = 2*self.convertEnergyToAngle(en)
    llen = self.convertAngleToEnergy(hltth/2.)
    print "Setting atth.hilim to %f, corresponds to en.lowlim %f" % (hltth, llen)
    self.atth.set_hilim(hltth)
    pass

  def setHiLimEn(self,en):
    lltth = 2*self.convertEnergyToAngle(en)
    hlen = self.convertAngleToEnergy(lltth/2.)
    print "Setting atth.lowlim to %f, corresponds to en.hilim %f" % (lltth, hlen)
    self.atth.set_lowlim(lltth)
    pass

  def getLowLimEn(self):
    """ Minimum achievable energy in virtual motor coordinates (keV), based on soft-limits of related physical stages """
    thhl = self.ath.get_hilim()
    tthhl = self.atth.get_hilim() / 2
    if thhl <= 90:
      EnCll = self.convertAngleToEnergy(thhl)
    else:
      EnCll = 0
    if tthhl <= 90:
      EnDll = self.convertAngleToEnergy(tthhl)
    else:
      EnDll = 0
      
    return max( EnCll, EnDll, self.convertAngleToEnergy(90)
               )
  pass
  

  def getHiLimEn(self):
    """ Maximum achievable energy in virtual motor coordinates (keV), based on soft-limits of related physical stages """
    thll = self.ath.get_lowlim()
    tthll = self.atth.get_lowlim() / 2
    if thll > 0:
      EnChl = self.convertAngleToEnergy(thll)
    else:
      EnChl = 1000
    if tthll > 0:
      EnDhl = self.convertAngleToEnergy(tthll)
    else:
      EnDhl = 1000
    return min(EnChl, EnDhl
               )
  pass 

  """ two functions are defined for angle-energy conversion: convertEnergyToAngle and convertAngleToEnergy """

  #snelson: have same in the class. And here we hardcode the PV. See if really necessary 
  #def getLatticeConst():
  #  return Pv.get("XPP:USER:Lattice_Const")
  """
  #a is the lattice constant
  a = 5.4307
  #hkl is the reflection of the analyzer crystal, a is the lattice constant
  hkl = n.array( [8,4,4] )
  #directLat is the matrix of the direct lattice, recLat is 2*pi* (directLat^-1)^T        
  directLat = n.matrix( ((a,0.,0.), (0.,a,0.), (0.,0.,a)) )    
  recLat = n.transpose( 2 * math.pi * ( n.linalg.inv(directLat) ) )
  #Ghkl is the diffraction vector, Dhkl the distance between the diffraction planes
  Ghkl = n.dot(recLat, hkl)
  Dhkl = 2 * math.pi / ( n.linalg.norm(Ghkl) )
  """

  def convertEnergyToAngle(self,energy):
    if energy > 50:
      print 'convertEnergyToAngle takes the energy in keV!'
      return None
    #a is the lattice constant
    #a = 5.4307
    a = self.getLatticeConst()
    #hkl is the reflection of the analyzer crystal, a is the lattice constant
    #hkl = n.array( [8,4,4] )
    #directLat is the matrix of the direct lattice, recLat is 2*pi* (directLat^-1)^T        
    directLat = n.matrix( ((a,0.,0.), (0.,a,0.), (0.,0.,a)) )    
    recLat = n.transpose( 2 * math.pi * ( n.linalg.inv(directLat) ) )
    #Ghkl is the diffraction vector, Dhkl the distance between the diffraction planes
    Ghkl = n.dot(recLat, self.hkl)
    Dhkl = 2 * math.pi / ( n.linalg.norm(Ghkl) )
  
    #Function that takes energy value and converts it to theta
    """Takes energy in keV and converts it in Theta in deg"""
    if 0 < energy:
      wavelenght = 12.3984193 / energy 
  
      #th is theta :)
      if (wavelenght / (2 * Dhkl) ) <= 1:
        th = math.asin( wavelenght / (2 * Dhkl) ) * 180 / math.pi
        return th
      else:
        minenergy = 12.3984193 / ( 2 * Dhkl)
        print "input energy %f is too small, min energy is %f" % (energy, minenergy)
        return None
    else:
      print "input energy %f is not reasonable, only > 0 keV is allowed" % (energy)
      return None

  def convertAngleToEnergy(self,th):
    #a is the lattice constant
    #a = 5.4307
    a = self.getLatticeConst()
    #hkl is the reflection of the analyzer crystal, a is the lattice constant
    #hkl = n.array( [8,4,4] )
    #directLat is the matrix of the direct lattice, recLat is 2*pi* (directLat^-1)^T        
    directLat = n.matrix( ((a,0.,0.), (0.,a,0.), (0.,0.,a)) )    
    recLat = n.transpose( 2 * math.pi * ( n.linalg.inv(directLat) ) )
    #Ghkl is the diffraction vector, Dhkl the distance between the diffraction planes
    Ghkl = n.dot(recLat, self.hkl)
    Dhkl = 2 * math.pi / ( n.linalg.norm(Ghkl) )
  
    #Function that takes Theta value and converts it to energy
    """ Takes theta in deg and converts it in energy in keV """
    if 0 < th <= 90:
    
      # energy is energy in keV:)
      energy = 12.3984193 / ( 2 * Dhkl * math.sin( th * math.pi / 180 ) )
      return energy
    else:
      print "input theta %f is not reasonable, only 0<...<=90Deg is allowed" % (th)
      return None

