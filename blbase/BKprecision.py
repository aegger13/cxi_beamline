import pypslog
import pyca
import psp.Pv as Pv
from blutil import estr

class BKprecision:

  def __init__(self,name,pv_Vset_set,pv_Vset_rb,pv_Aset_set,pv_Aset_rb,pv_Vread,pv_Aread,pv_Vmax_set,pv_Vmax_rb,pv_Amax_rb):
    self.pv_Vset_set = pv_Vset_set
    self.pv_Vset_rb  = pv_Vset_rb
    self.pv_Aset_set = pv_Aset_set
    self.pv_Aset_rb  = pv_Aset_rb
    self.pv_Vread    = pv_Vread
    self.pv_Aread    = pv_Aread
    self.pv_Vmax_set = pv_Vmax_set
    self.pv_Vmax_rb  = pv_Vmax_rb
    self.pv_Amax_rb  = pv_Amax_rb
    self.name = name
  
  def status(self):
    volt=Pv.get(self.pv_Volt)
    onoff=Pv.get(self.pv_OnOff)
    #if onoff==0:
      #sstatus=estr("On",color='green',type='bold')
    #elif  onoff==1:
      #sstatus=estr("Off",color='red',type='bold')
    #else:
      #sstatus=estr("Not Known",color='white',type='normal')
    str1 ="%s:" % self.name
    str2 =" %s\n" % sstatus
    str3 ="Level:"
    str4 =" %d%%" % (self.level()*100)
    str = str1.rjust(10)+str2.ljust(5)+str3.rjust(10)+str4.ljust(5)
    return str

  def setV(self,value):
    Pv.put(self.pv_Vset_set,value)

  def rdSetV(self):
    Pv.get(self.pv_Vset_rb)

  def setA(self,value):
    Pv.put(self.pv_Aset_set,value)

  def rdSetA(self):
    Pv.get(self.pv_Aset_rb)
  
  def getV(self):
    Pv.get(self.pv_Vread)

  def getA(self):
    Pv.get(self.pv_Aread)

  
  def setVmax(self,value):
    Pv.put(self.pv_Vmax_set,value)

  def rdVmax(self):
    Pv.get(self.pv_Vmax_rb)

  def rdAmax(self):
    Pv.get(self.pv_Amax_rb)

  def info(self):
    """ Prints information about the BKprecision power supply """
    str="\n    %s\n" % (self.status())
    print str

  def __repr__(self):
    return self.status()
