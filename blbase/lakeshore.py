import pyca
import psp.Pv as Pv
from blutil import estr
from time import sleep

class lakeshore:

  def __init__(self,name,pv_setTsetpoint,pv_getTsetpoint,pv_getTemp,tolerance=.1):
    self.name = name
    self.pv_setTsetpoint = pv_setTsetpoint
    self.pv_getTsetpoint = pv_getTsetpoint
    self.pv_getTemp = pv_getTemp
    self.tolerance = tolerance
 
  def get_Temperature(self):
    T = Pv.get(self.pv_getTemp)
    return T

  def set_Temperature(self,value):
    Pv.put(self.pv_setTsetpoint,value)

  def getSetIsDiff(self):
    T    = Pv.get(self.pv_getTemp)
    Tset = Pv.get(self.pv_getTsetpoint)
    DT = T-Tset
    return DT

  def wait(self):
    while abs(self.getSetIsDiff())>self.tolerance:
      sleep(.2)

  def status(self):
    Tset = Pv.get(self.pv_getTsetpoint)
    T = self.get_Temperature()
    DT = self.getSetIsDiff()
    sstatus = estr('Lakeshore '+self.name+'\n',color='green',type='bold')
    sstatus += '  Current Temperature = ' + str(T) + '; current setpoint = ' + str(Tset) + '\n'
    if abs(self.getSetIsDiff())>self.tolerance:
      sstatus += estr('  Difference '+str(DT)+' outside tolerance ('+str(self.tolerance)+')',color='red',type='bold')
    else:
      sstatus += estr('  Difference '+str(DT)+' with tolerance ('+str(self.tolerance)+')',color='green',type='bold')

    
    #else:
      #sstatus=estr("Not Known",color='white',type='normal')
    #str1 ="%s:" % self.name
    #str2 =" %s\n" % sstatus
    #str3 ="Level:"
    #str4 =" %d%%" % (self.level()*100)
    #str = str1.rjust(10)+str2.ljust(5)+str3.rjust(10)+str4.ljust(5)
    return sstatus


  def __repr__(self):
    return self.status()
