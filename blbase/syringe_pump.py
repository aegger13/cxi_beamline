import pyca
import psp.Pv as Pv
from time import sleep

class SyringePump:

  def __init__(self,name,pv_base,pv_TTL,Vlow=0,Vhigh=5):
    self.name = name
    self.pv_base = pv_base
    self.pv_TTL = pv_TTL
    self.Vhigh = Vhigh
    self.Vlow = Vlow
    Pv.put(pv_base,5)
    Pv.put(pv_TTL,0)


  def toggle(self):
    Pv.put(self.pv_TTL,self.Vhigh)
    sleep(.1)
    Pv.put(self.pv_TTL,self.Vlow)

