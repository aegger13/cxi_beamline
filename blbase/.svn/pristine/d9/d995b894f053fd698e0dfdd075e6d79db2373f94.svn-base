import time
from psp import Pv
from virtualmotor import VirtualMotor

class PvMotor(VirtualMotor):
  def __init__(self, pv, name, pv_rbv=None, pv_sioc=None, waitTime=0.2, pv_to_mot=lambda x:x, mot_to_pv=lambda x:x, motorsobj=None, egu="mm"):
    super(PvMotor, self).__init__(name, self._pv_move, self._pv_wm, self._pv_wait, motorsobj=motorsobj, egu=egu)
    self.pvname = pv
    self._pv = Pv.Pv(pv)
    if pv_rbv is None:
      self._pv_rbv = self._pv
    else:
      self._pv_rbv = Pv.Pv(pv_rbv)
    self._pv_sioc = pv_sioc
    self._waitTime = waitTime
    self._pv_to_mot = pv_to_mot
    self._mot_to_pv = mot_to_pv

  def _pv_move(self, value):
    return self._pv.put(self._mot_to_pv(value))

  def _pv_wm(self):
    return self._pv_to_mot(self._pv_rbv.get())

  def _pv_wait(self):
    if self._pv is self._pv_rbv:
      time.sleep(self._waitTime)
    else:
      self._pv_rbv.wait_for_value(self._pv.get())

  def reset(self):
    if self._pv_sioc is None:
      print "no SIOC pvname defined. Cannot reset."
    else:
      Pv.put(self._pv_sioc+":SYSRESET",1)
