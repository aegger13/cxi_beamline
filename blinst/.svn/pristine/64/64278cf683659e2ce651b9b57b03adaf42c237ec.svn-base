#!/usr/bin/python
import time

class BeLens:
  """ Class to control the Beryllium Lenses """

  def __init__(self,x,y,z,name="Be Lens",attObj=None):
    self.x   = x
    self.y   = y
    self.z   = z
    self.name = name
    self.motors = {
      "x": x,
      "y": y,
      "z": z
      }
    self._attObj = attObj

  def move_z(self, pos, safe=True):
    if safe and self._attObj is not None:
      is_safe = self._make_safe()
      if not is_safe:
        print "Aborting move_Z for safety."
        return
    self.z.mv(pos)

  def _make_safe(self):
    filt, thk = self._attObj.filters[0], 0
    for f in self._attObj.filters:
      t = f.d()
      if t > thk:
        filt, thk = f, t
    filt.movein()
    time.sleep(0.01)
    filt.wait()
    if filt.isin():
      print "REMEMBER: beam stop attenuator moved in to protect instruments from Be lens"
      safe = True
    else:
      print "WARNING: Beam stop attenuator did not move in!"
      safe = False
    return safe

  def status(self):
    str = "** %s Status **\n\t%10s\t%10s\t%10s\n" % (self.name,"Motor","User","Dial")
    keys = self.motors.keys()
    keys.sort()
    for key in keys:
       m = self.motors[key]
       str += "\t%10s\t%+10.4f\t%+10.4f\n" % (key,m.wm(),m.wm_dial())
    return str
  
  def __repr__(self):
    return self.status()
