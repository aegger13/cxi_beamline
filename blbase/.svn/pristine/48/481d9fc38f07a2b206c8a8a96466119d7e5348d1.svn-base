#
# nanocube implementation
#
import psp.Pv as Pv
from time import sleep

class nano:
  def __init__ (self, basePV, iocPV):
    self.basePV = basePV
    self.iocPV = iocPV
    self.__getpos =  ':TELLPOSITION'
    self.__setpos =  ':MOVEABSOLUTE'
    self.__getspeed =  ':TELLVELOCITY'
    self.__setspeed =  ':SETVELOCITY'
    self.__x = "01:X"
    self.__y = "02:Y"
    self.__z = "03:Z"

  def get_x(self):
    return Pv.get(self.basePV+self.__x+self.__getpos)

  def get_y(self):
      return Pv.get(self.basePV+self.__y+self.__getpos)

  def get_z(self):
      return Pv.get(self.basePV+self.__z+self.__getpos)

  def move_x(self, v):
    return Pv.put(self.basePV+self.__x+self.__setpos, v)

  def move_y(self, v):
    return Pv.put(self.basePV+self.__y+self.__setpos, v)

  def move_z(self, v):
    return Pv.put(self.basePV+self.__z+self.__setpos, v)
  
  def get_x_speed(self):
    return Pv.get(self.basePV+self.__x+self.__getspeed)*1e3

  def get_y_speed(self):
    return Pv.get(self.basePV+self.__y+self.__getspeed)*1e3

  def get_z_speed(self):
    return Pv.get(self.basePV+self.__z+self.__getspeed)*1e3

  def set_x_speed(self, v):
    return Pv.put(self.basePV+self.__x+self.__setspeed, v/1e3)

  def set_y_speed(self, v):
    return Pv.put(self.basePV+self.__y+self.__setspeed, v/1e3)

  def set_z_speed(self, v):
    return Pv.put(self.basePV+self.__z+self.__setspeed, v/1e3)

  def wait(self):
    sleep(0.1)

  def reboot(self):
    return Pv.put("%s:SYSRESET"%self.iocPV, 1)

