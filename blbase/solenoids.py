# Scott Stubbs, May 2017
# Simple class to control 8-channel solenoid chassis.


import psp.Pv as Pv
import numpy as np
from blutil import estr

class Solenoid_Chassis():

    '''Simple class to control 8-channel solenoid chassis.
       Structure of PVs expected to be (BASE):(NUM):(OUT, IN, or CMD)
    
       solenoids.status(num)  : returns the status of solenoid (num)
       solenoids.moveOut(num)    : energizes solenoid (num)
       solenoids.moveIn(num)   : de-energizes solenoid (num)
    '''
    
    def __init__(self, basepv, name):
        self._basepv = basepv
        self._name=name

#    def isout(self,num):
#       if num >= 0 and num < 9:
#              if Pv.get(self._basepv+':OUT')==1 : return True
#              else : return False
#       else:
#              print "Solenoid number must be between 1-8"
#
#    def isout(self,num):
#       if num >= 0 and num < 9:
#              if Pv.get(self._basepv+':OUT')==1 : return True
#              else : return False
#       else:
#              print "Solenoid number must be between 1-8"
        
    def status(self,num):
      '''Returns the status of the solenoid.'''
      if num >= 0 and num < 9:  statstr=self._name +' is '
      else:
             print "Solenoid number must be between 1-8"
             return
      if Pv.get(self._basepv + ':' + num + ':OUT')==1 :
             statstr+=estr('out',color='green',type='normal')
      elif Pv.get(self._basepv + ':' + num + ':IN')==1 :
             statstr+=estr('in',color='red',type='normal')
      else:
             statstr+=estr('neither out nor in - perhaps moving?',color='yellow',type='fault')
      return(statstr)

    def moveOut(self,num):
       '''Energizes solenoid on valve.'''
       if num >= 0 and num < 9:
             Pv.put(self._basepv + ':' + num + ':CMD',1)
       else:
             print "Solenoid number must be between 1-8"

    def moveIn(self,num):
       '''De-energizes solenoid on valve'''
       if num >= 0 and num < 9:
              Pv.put(self._basepv + ':' + num + ':CMD',0)
       else:
              print "Solenoid number must be between 1-8"

