#!/usr/bin/python
# This module provides support 
# for the XCS Large Area Detector Mover (LADM or LAM)
# for the XCS beamline (@LCLS)
# 
# Author:         Daniel Flath (SLAC)
# Created:        Aug 19, 2011
# Modifications:
#   Aug 19, 2011 DF
#       first version

# TODO: This should be replaced by a generic 2D stage

class Beamstop:
  """ Class to control the XCS Beamstop """

  def __init__(self,radial,transverse,radius):
    self.r          = radial
    self.t          = transverse
    self.radius     = radius

  def status(self):
    str = "** \"%smm\" Beam-stop Status **\n" % (self.radius)
    str += "\t(radial, transverse) [user]: %+.4f, %+.4f\n" % (self.r.wm(),self.t.wm())
    str += "\t(radial, transverse) [dial]: %+.4f, %+.4f\n" % (self.r.wm_dial(),self.t.wm_dial())
    return str
  
  def __repr__(self):
    return self.status()
