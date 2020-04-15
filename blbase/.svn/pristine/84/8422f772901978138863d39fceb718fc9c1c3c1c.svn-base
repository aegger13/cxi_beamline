from blutil import config
from blutil import estr
import psp.Pv as Pv
from time import time,sleep



class AIO:
  def __init__(self, inputPV, outputPV):
    self.chRange = range(16)
    self.inputPV = inputPV
    self.outputPV = outputPV

  def getAI(self, ch):
    if ch in self.chRange:
      chPV = "%s:in%d.VAL" % (self.inputPV, ch)
      return Pv.get(chPV)
    else:
      print "channel number needs to be between 0 and 15"

  def getAO(self, ch):
    if ch in self.chRange:
      chPV = "%s:out%d.VAL" % (self.outputPV, ch)
      return Pv.get(chPV)
    else:
      print "channel number needs to be between 0 and 15"

  def setAO(self, ch, value):
    if ch in self.chRange:
      chPV = "%s:out%d" % (self.outputPV, ch)
      Pv.put(chPV, value)
    else:
      print "channel number needs to be between 0 and 15"

  def status(self):
    print self.status_str()

  def __repr__(self):
    return self.status()

  def status_str(self):
    s =  "**** Analog Input Output Status ****\n"
    s += "\nInput at %s:\n" % self.inputPV
    for i in range(8):
      chPV1 = "%s:in%d.VAL" % (self.inputPV, i)
      chPV2 = "%s:in%d.VAL" % (self.inputPV, i+8)
      s += "  ch%d: %.4f       ch%d: %.4f \n" % (i, Pv.get(chPV1), i+8,  Pv.get(chPV2))
    
    s += "\nOutput at %s:\n" % self.outputPV
    for i in range(8):
      chPV1 = "%s:out%d.VAL" % (self.outputPV, i)
      chPV2 = "%s:out%d.VAL" % (self.outputPV, i+8)
      s += "  ch%d: %.4f       ch%d: %.4f \n" % (i, Pv.get(chPV1), i+8,  Pv.get(chPV2))
    s += "\n************************************\n"
    return s
