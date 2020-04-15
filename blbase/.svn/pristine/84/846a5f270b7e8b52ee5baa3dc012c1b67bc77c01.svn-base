import sys
import psp.Pv as Pv
from blutil.pypslog import logprint
from virtualmotor import VirtualMotor
import time

class SaPiezo(VirtualMotor):
    def __init__(self, motorsobj, name, pvbase):
        self.__pvbase = pvbase
        VirtualMotor.__init__(self,
                              name,
                              self.__move,
                              self.__wm,
                              self.__wait,
                              egu = "mm",
                              motorsobj = motorsobj,
                              )

        pass

    def __getstepsize(self):
        return Pv.get(self.__pvbase+":STEP_INC")

    def __wm(self):
        return Pv.get(self.__pvbase+":SENS_POS")/1.0e6

    def __move(self,pos):
        Pv.put(self.__pvbase+":GO",0)
        Pv.put(self.__pvbase+":STOP",1)
        Pv.put(self.__pvbase+":CTRL_POS",int(pos*1.0e6/self.__getstepsize()))
        Pv.put(self.__pvbase+":GO",1)
        Pv.put(self.__pvbase+":STOP",0)
        pass

    def __wait(self):
        done=False
        while not done:
            done = (Pv.get(self.__pvbase+":MOVE_DONE") == 1)
            if not done:
                time.sleep(.1)
            else:
                return
            pass
        pass

    #def mvr(self,delta):
    #    self.move(self.wm()+delta)

    pass
