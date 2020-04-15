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


# TODO:  This should be replaced by a generic 2D manipulator class...

class Aerotech:
  """ Class to control the XCS LADM """

  def __init__(self,x,y):
    self.x   = x
    self.y   = y

  def status(self):
    str = "** Detector Translation Status **\n"
    str += "\t(x, y) [user]: %+.4f, %+.4f\n" % (self.x.wm(),self.y.wm())
    str += "\t(x, y) [dial]: %+.4f, %+.4f\n" % (self.x.wm_dial(),self.y.wm_dial())
    return str
  
  def __repr__(self):
    return self.status()
