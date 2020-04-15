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

import beamstop

class Beamstops:
  """ Class to control the XCS Beamstops """

  def __init__(self):
    self.beamstops=[]

  def addBeamstop(self,beamstop):
    self.beamstops.append(beamstop)

  def status(self):
    str = "** LADM Beam-stops **\n"
    for bs in self.beamstops:
      str += bs.status()
    return str
  
  def __repr__(self):
    return self.status()
