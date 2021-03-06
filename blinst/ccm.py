#!/usr/bin/python
# This module provides support 
# for the XPP/XCS CCM monochromator
# for the XPP/XCS beamlines (@LCLS)
# 
# Author:         Marco Cammarata (SLAC)
# Created:        Aug 27, 2010
# Modifications:
#   Aug 27, 2010 MC
#       first version

import numpy as n
import sys
from blutil import estr
from psp import Pv
from blutil.pypslog import logprint

gR = 3.175
#    self.__D = 232.15
#    self.__theta0 = 15.05
gD = 231.303
#    gTheta0 = 15.08219; # original calibration

#defaults
#gTheta0 = 15.18219; # calibration for split and delay
#gTheta0 = 14.983; # quick calibration Jul22 4am
#gTheta0 = 14.9786; # better calibration Jul27 using the inflection point at data resolution and edges of Ni,Ti and Zr
#gTheta0 = 14.9694; # better calibration Jul27 using the inflection point of a splinefit only using Ti edge, the Ti edge was best resolved and is closest to the energy for L333.
gTheta0 = 14.9792; # better calibration Jul27 using the inflection point at (probably) improved resolution using a splinefit.


#definitions for Si Xtals
#gSi111dspacing = 3.13556044         # original from way back
gSi111dspacing = 3.1356011499587773  # most recent, xpp
gSi511dspacing = 1.0452003833195924  # 511, xcs

#defaults
gdspacing = gSi111dspacing


#TODO: dflath 2015-09-17 - Use the common/vernier module instead

class CCM:
  """ Class to control the XPP/XCS CCM """
  def __init__(self,x1,x2,y1,y2,y3,alio,t2coarse,t2fine,chi2,PVbase=None,vernierPV='MCC:USR:PHOTON:ENERGY'):
    self.x1   = x1
    self.x2   = x2
    self.y1   = y1
    self.y2   = y2
    self.y3   = y3
    self.alio = alio
    self.theta2fine = t2fine
    self.theta2coarse = t2coarse
    self.chi2 = chi2
    self.__inpos=dict()
    self.E = None
    self.theta = None
    # use .set_inpos or .set_outpos
    self.__inpos["x1"]=None
    self.__inpos["x2"]=None
    self.__inpos["y1"]=None
    self.__inpos["y2"]=None
    self.__inpos["y3"]=None
    self.__outpos=dict()
    self.__outpos["x1"]=None
    self.__outpos["x2"]=None
    self.__outpos["y1"]=None
    self.__outpos["y2"]=None
    self.__outpos["y3"]=None
    self.__vernierPV = vernierPV
    if (PVbase is None):
      self.__pv_E = None
    else:
      self.__pv_E = PVbase + ":CCM:E"
      
#    self.__wmccm()

  def set_inpos(self,x,y):
    """ Sets the CCM In position """
    self.__inpos["x1"]=x
    self.__inpos["x2"]=x
    self.__inpos["y1"]=y
    self.__inpos["y2"]=y
    self.__inpos["y3"]=y

  def set_outpos(self,x,y):
    """ Sets the CCM Out position """
    self.__outpos["x1"]=x
    self.__outpos["x2"]=x
    self.__outpos["y1"]=y
    self.__outpos["y2"]=y
    self.__outpos["y3"]=y

  def movey(self,pos):
    """ Moves y1, y2, y3 simultaneously """
#    myprint("moving x1,x2 to %f,%f" % (x1,x2))
#    myprint("moving y1,y2,y3 to %f,%f" % (y1,y2,y3))
    self.y1.move(pos); self.y2.move(pos); self.y3.move(pos)

  def movex(self,pos):
    """ Moves x1, x2 simultaneuosly """
#    myprint("moving x1,x2 to %f,%f" % (x1,x2))
#    myprint("moving y1,y2,y3 to %f,%f" % (y1,y2,y3))
    self.x1.move(pos); self.x2.move(pos);

  def movein(self):
    """ Moves CCM to the set In position """
    x1=self.__inpos["x1"];
    x2=self.__inpos["x2"];
    y1=self.__inpos["y1"];
    y2=self.__inpos["y2"];
    y3=self.__inpos["y3"];
#    myprint("moving x1,x2 to %f,%f" % (x1,x2))
    self.x1.move(x1); self.x2.move(x2)
    self.x1.wait(); self.x2.wait()
#    myprint("moving y1,y2,y3 to %f,%f" % (y1,y2,y3))
#    self.y1.move(y1); self.y2.move(y2); self.y3.move(y3)

  def moveout(self):
    """ Moves CCM to the set Out position """
    x1=self.__outpos["x1"];
    x2=self.__outpos["x2"];
    y1=self.__outpos["y1"];
    y2=self.__outpos["y2"];
    y3=self.__outpos["y3"];
#    myprint("moving y1,y2,y3 to %f,%f" % (y1,y2,y3))
#    self.y1.move(y1); self.y2.move(y2); self.y3.move(y3)
#    self.y1.wait(); self.y2.wait(); self.y3.wait()
#    myprint("moving x1,x2 to %f,%f" % (x1,x2))
    self.x1.move(x1); self.x2.move(x2)

  def wait(self):
    """ Returns when x1,x2,y1,y2,y3 are not moving """
    self.y1.wait(); self.y2.wait(); self.y3.wait()
    self.x1.wait(); self.x2.wait()
    self.alio.wait()

  def __update_PV(self):
    if (self.__pv_E is not None):
      Pv.put(self.__pv_E,self.__E)
      
  def moveE(self,E):
    """ E in keV """
    if (E>2000):
      E=E/1e3
    alio = EToAlio(E)
    self.alio.move(alio)

  def moveEwithVernier(self,E,vernierThresKeV=.003):
    """ E in keV """
    if (E>2000):
      E=E/1e3
    Ever0 = Pv.get(self.__vernierPV)/1000.
    if n.abs(Ever0-E) > vernierThresKeV:
      Pv.put(self.__vernierPV,E*1000)
    alio = EToAlio(E)
    self.alio.move(alio)

  def moveVernierEphot(self,E):
    """ E in keV """
    if (E>2000):
      E=E/1e3
    Pv.put(self.__vernierPV,E*1000)

  def readVernierEphot(self):
    """ E in keV """
    Ever = Pv.get(self.__vernierPV)/1000.
    return Ever

  def __wmccm(self):
    x=self.alio.wm(); 
    self.__theta = alioToTheta(x)
    self.__wavelength = thetaToWavelength(self.__theta)
    self.__E = wavelengthToE(self.__wavelength)
    self.__resolution = (alioToE(x-1e-4)-alioToE(x))/1e-4
    self.__x1pos = self.x1.wm()
    self.__x2pos = self.x2.wm()
#    self.__y1pos = self.y1.wm()
#    self.__y2pos = self.y2.wm()
#    self.__y3pos = self.y3.wm()
    self.__update_PV()

  def wmE(self):
   """ returns the energy in keV"""
   self.__wmccm()
   return self.__E

  def moveTheta(self,Theta):
    """ Theta in degrees """
    alio = thetaToAlio(Theta)
    self.alio.move(alio)

  def wmTheta(self):
   """ returns theta in degrees"""
   self.__wmccm()
   return self.__theta

  def isin(self):
    """ returns True if the x positions match the predefined ones within 5um """
    tolerance = 5e-3
    c1 = abs( self.x1.wm() - self.__inpos["x1"]) < tolerance
    c2 = abs( self.x2.wm() - self.__inpos["x2"]) < tolerance
    return (c1 and c2)

  def status(self):
    self.__wmccm()
    x1= self.__x1pos; x2= self.__x2pos;
    #y1= self.__y1pos; y2= self.__y2pos; y3= self.__y3pos
    str  = "alio   (mm): %.4f\n" % self.alio.wm()
    str += "angle (deg): %.3f\n" % self.__theta
    str += "lambda  (A): %.4f\n" % self.__wavelength
    str += "Energy (keV): %.4f\n" % self.__E
    str += "res (eV/mm): %.1f\n" % (self.__resolution*1e3)
    str += "res (eV/um): %.2f\n" % (self.__resolution)
    str += "x @ (mm): %.3f [x1,x2=%.3f,%.3f]\n" % ((x1+x2)/2,x1,x2)
    #str += "y @ (mm): %.3f [y1,y2,y3=%.3f,%.3f,%.3f]\n" % ((y1+y2+y3)/3,y1,y2,y3)
    return str

  def __repr__(self):
    return self.status()

def thetaToAlio(theta):
  """ Function that converts theta angle (deg) to alio position (mm) """
  t_rad = (theta-gTheta0)*n.pi/180.
  x = gR*(1/n.cos(t_rad)-1)+gD*n.tan(t_rad)
  return x

def alioToTheta(alio):
  """ Function that converts alio position (mm) to theta angle (deg) """
  return gTheta0 + 180/n.pi*2*n.arctan( (n.sqrt(alio**2+gD**2+2*gR*alio)-gD) / (2*gR+alio) )

def thetaToWavelength(theta):
  """ Function that converts theta angle (deg) to wavelength (A) """
  return 2*gdspacing*n.sin(theta/180*n.pi)

def wavelengthToTheta(wavelength):
  """ Function that converts wavelength (A) to theta angle (deg) """
  return 180./n.pi*n.arcsin(wavelength/2/gdspacing )

def alioToWavelength(alio):
  """ Function that converts alio position (mm) to wavelength (A) """
  theta = alioToTheta(alio)
  return thetaToWavelength(theta)

def alioToE(alio):
  """ Function that converts alio position (mm) to photon energy (keV) """
  l = alioToWavelength(alio)
  return wavelengthToE(l)

def wavelengthToE(wavelength):
  """ Fucntion that converts wavelength (A) to photon energy (keV) """
  return 12.39842/wavelength

def EToWavelength(E):
  """ Function that converts photon energy (keV) to wavelength (A) """
  return 12.39842/E

def EToAlio(E):
  """ Function that converts photon energy (keV) to alio position (mm) """
  l = EToWavelength(E)
  t = wavelengthToTheta(l)
  alio = thetaToAlio(t)
  return alio
