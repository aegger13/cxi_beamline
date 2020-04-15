#!/usr/bin/python
# This module provides support 
# for the Large Area Detector Mover (LADM or LAM)
# 
# Author:         Daniel Flath (SLAC)
# Created:        Aug 19, 2011
# Modifications:
#   Aug 19, 2011 DF
#       first version

import numpy

class JJSlits:
  """ Class to control the Beamstop """

  def __init__(self,svg,svo,shg,sho,name):
    self.svg  = svg
    self.svo  = svo
    self.shg  = shg
    self.sho  = sho
    self.name = name

  def status(self):
    str = "** \"%s\" JJ-Slit Status **\n" % (self.name)
    str += "\t(svg, svo, shg, sho) [user]: %+.4f, %+.4f, %+.4f, %+.4f\n" % (self.svg.wm(),self.svo.wm(),self.shg.wm(),self.sho.wm())
    str += "\t(svg, svo, shg, sho) [dial]: %+.4f, %+.4f, %+.4f, %+.4f\n" % (self.svg.wm_dial(),self.svo.wm_dial(),self.shg.wm_dial(),self.sho.wm_dial())
    return str
  
  def __repr__(self):
    return self.status()

  def __call__(self,hg,vg=None):
    if vg is None:
      vg = hg
    self.mv_hg(hg)
    self.mv_vg(vg)

  def wm_ho(self):
    return self.sho.wm()
  def wm_hg(self):
    return self.shg.wm()
  def wm_vo(self):
    return self.svo.wm()
  def wm_vg(self):
    return self.svg.wm()

  def mv_ho(self,offset=0):
    self.sho.move(offset)

  def set_ho(self,newoffset=0):
    self.sho.set(newoffset)

  def mv_vo(self,offset=0):
    self.svo.move(offset)

  def set_vo(self,newoffset=0):
    self.svo.set(newoffset)

  def mv_hg(self,gap=None):
    if (gap is None):
      return
    self.shg.move(gap)

  def set_hg(self,newgap=0):
    self.shg.set(newgap)

  def mv_vg(self,gap=None):
    if (gap is None):
      return
    self.svg.move(gap)

  def set_vg(self,newgap=0):
    self.svg.set(newgap)

  def wait(self):
    self.svg.wait()
    self.svo.wait()
    self.shg.wait()
    self.sho.wait()

  def waith(self):
    self.shg.wait()
    self.sho.wait()

  def waitv(self):
    self.svg.wait()
    self.svo.wait()
