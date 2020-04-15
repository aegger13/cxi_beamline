import numpy
import sys
from blutil import estr
from blbase.motorutil import tweak2D
import psp.Pv as Pv

class XYZStage:
  """ Class that defines generic XYZ stage, with functions to get to next targets. Basicly combines three motors in one object.
  """
  def __init__(self,x,y,z,nx=0.5,ny=0,nxd='None',nyd='None',name=""):
      self.x=x
      self.y=y
      self.z=z
      self._nx=nx
      self._ny=ny
      self._name=name

      self._savepvx="MEC:NOTE:DOUBLE:37"
      self._savepvy="MEC:NOTE:DOUBLE:38"
      self._savepvz="MEC:NOTE:DOUBLE:39"

      if nxd=='None':
        self._nxd=-self._ny
      else: self._nxd=nxd
      
      if nyd=='None':
        self._nyd=self._nx
      else: self._nyd=nyd

      self.__name=name

  def next(self,n=1):
      self.y.mvr(n*self._ny)
      self.x.umvr(n*self._nx)

  def down(self,n=1):
      self.x.mvr(n*self._nxd)
      self.y.umvr(n*self._nyd)

  def up(self,n=1):
      self.down(-n)

  def back(self,n=1):
      self.next(-n)

  def tweakxy(self,step=0.1,dirx=1,diry=-1):
    tweak2D(self.x,self.y,mothstep=step,motvstep=step,dirh=dirx,dirv=diry)

  def save_position(self):
    '''saves the current position of the target stage in the user pvs.

       The user pvs are hard coded, so the same for ever xyzstage that is
       defined. The last save position can be recovered with the return.
    '''
    print 'saving current position of the xyzstage ' + self._name
    Pv.put(self._savepvx,self.x.wm())
    Pv.put(self._savepvy,self.y.wm())
    Pv.put(self._savepvz,self.z.wm())

  def return_position(self):
    ''' returns the target stage to the last saved position.

        the target position is save with .save()
    '''
    print 'moves the xyzstage ' + self._name + 'to the last saved position'
    self.x.mv(Pv.get(self._savepvx))
    self.y.mv(Pv.get(self._savepvy))
    self.z.mv(Pv.get(self._savepvz))

    
class X2YZStage:
  """ Class that defines a generic XYZ stage with a translation (called tgx) on top of it, with functions to get to next targets. Basicly combines four motors in one object. It uses the translation on top to move from one position to the other (supposedly big moves).
  """
  def __init__(self,x,y,z,tgx,ntgx=0.6,ny=0,ntgxd='None',nyd='None',name=""):
      self.x=x
      self.y=y
      self.z=z
      self.tgx=tgx
      self._ntgx=ntgx
      self._ny=ny
      self._name=name

      if self._name == 'pci target':
        self._savepvx="MEC:NOTE:DOUBLE:51"
        self._savepvy="MEC:NOTE:DOUBLE:52"
        self._savepvz="MEC:NOTE:DOUBLE:70"
        self._savepvtgx="MEC:NOTE:DOUBLE:71"
      else:
        self._savepvx="MEC:NOTE:DOUBLE:37"
        self._savepvy="MEC:NOTE:DOUBLE:38"
        self._savepvz="MEC:NOTE:DOUBLE:39"
        self._savepvtgx="MEC:NOTE:DOUBLE:40"

      if ntgxd=='None':
        self._ntgxd=-self._ny
      else: self._ntgxd=ntgxd

      if nyd=='None':
        self._nyd=self._ntgx
      else: self._nyd=nyd
      self.__name=name

  def next(self,n=1):
      self.y.mvr(n*self._ny)
      self.tgx.umvr(n*self._ntgx)

  def down(self,n=1):
      self.tgx.mvr(n*self._ntgxd)
      self.y.umvr(n*self._nyd)

  def up(self,n=1):
      self.down(-n)

  def back(self,n=1):
      self.next(-n)

  def tweakxy(self,step=0.1,dirx=1,diry=-1):
    if self._name == 'pci target':
      tweak2D(self.x,self.y,mothstep=step,motvstep=step,dirh=dirx,dirv=diry)
    else:
      tweak2D(self.tgx,self.y,mothstep=step,motvstep=step,dirh=dirx,dirv=diry)

  def tweakzy(self,step=0.1,dirz=1,diry=-1):
    if self._name == 'pci target':
      tweak2D(self.z,self.y,mothstep=step,motvstep=step,dirh=dirz,dirv=diry)
    else:
      tweak2D(self.z,self.y,mothstep=step,motvstep=step,dirh=dirz,dirv=diry)

  def save_position(self):
    '''saves the current position of the target stage in the user pvs.

       The user pvs are hard coded, so the same for ever xyzstage that is
       defined. The last save position can be recovered with the return.
    '''
    print 'saving current position of the xyzstage ' + self._name
    Pv.put(self._savepvx,self.x.wm())
    Pv.put(self._savepvy,self.y.wm())
    Pv.put(self._savepvz,self.z.wm())
    Pv.put(self._savepvtgx,self.tgx.wm())

  def return_position(self):
    ''' returns the target stage to the last saved position.

        the target position is save with .save()
    '''
    print 'moves the xyzstage ' + self._name + 'to the last saved position'
    self.x.mv(Pv.get(self._savepvx))
    self.y.mv(Pv.get(self._savepvy))
    self.z.mv(Pv.get(self._savepvz))
    self.tgx.mv(Pv.get(self._savepvtgx))
