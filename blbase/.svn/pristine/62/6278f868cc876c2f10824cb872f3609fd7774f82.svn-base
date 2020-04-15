""" Generic functions that can act on multiple motors """

import psp.Pv as Pv
from blutil import estr
from blutil import notice
from blutil import keypress
import pyca
import sys
import motor as mmm
import virtualmotor as vvv
import numpy as np

def select_MMS_motors(motor_obj,string=None):
  """ returns a list of PV names found in the motors object (for example motors)
      Optionally a string can be used to select only those PVnames that contain that string """
  nlist = motor_obj.__dict__.keys()
  mlist = []
  for i in nlist:
    m = motor_obj.__getattribute__(i)
    try:
      if (m.pvname.find("MMS") > 0):
        if (string is None):
          mlist.append(m.pvname)
        elif (m.pvname.find(string)>0):
          mlist.append(m.pvname)
        else:
          pass
    except:
      pass
  mlist.sort()
  return mlist


def select_CLZ_motors(motor_obj,string=None):
  """ returns a list of PV names found in the motors object (for example motors)
      Optionally a string can be used to select only those PVnames that contain that string """
  nlist = motor_obj.__dict__.keys()
  mlist = []
  for i in nlist:
    m = motor_obj.__getattribute__(i)
    try:
      if (m.pvname.find("CLZ") > 0):
        if (string is None):
          mlist.append(m.pvname)
        elif (m.pvname.find(string)>0):
          mlist.append(m.pvname)
        else:
          pass
    except:
      pass
  mlist.sort()
  return mlist


def save_motors_pos(motor_list,outfile=None):
  """ display (and optionally save if outfilename is given) the motor positions for
      a list of motors (not PVs!) """
  if (not isinstance(motor_list,list)):
    motor_list = [motor_list]
  for m in motor_list:
    print m.name,m.wm()
  if (outfile is not None):
    f=open(outfile,"w")
    for m in motor_list:
      f.write("%s %e\n" % (m.name,m.wm()))
    f.close()
    

def load_motors_pos(motorsobj,infile):
  """ load and move motors, motor names and positions are taken from file, motors
      are found in motorsobj (for example motors) """
  f=open(infile,"r")
  lines = f.readlines()
  f.close()
  for l in lines:
    (mname,pos) = l.split(); pos=float(pos)
    print mname,pos
    m = find_motor_by_name(motorsobj,mname)
    if (m is not None):
      print "moving %s to %e (previous position %e)" % (mname,pos,m.wm())
      m.move(pos)

def show_motors_pos(infile):
  f=open(infile,"r")
  lines = f.readlines()
  f.close()
  for l in lines:
    (mname,pos) = l.split(); pos=float(pos)
    print mname,pos

def find_motor_by_name(motor_obj,mname):
  """ returns first motor object with given name, returns None if not found"""

  motors=motor_obj.__dict__.keys()
  for m in motors:
    if isinstance(motor_obj.__dict__[m],(mmm.Motor,vvv.VirtualMotor)):
      ## make a list of motor to handle filt[1],filt[2], ...
      if ( not isinstance(motor_obj.__getattribute__(m),list) ):
        mlist = [motor_obj.__getattribute__(m)]
      else:
        mlist = motor_obj.__getattribute__(m)
      for mm in mlist:
  #      if (motor_obj.__getattribute__(mm).name == mname):
        if (mm.name == mname):
          return mm
          break
  return None


def tweak(motor,step=0.1,direction=1):
  help_text = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
  help_text += "g = go abs, s = set"
  print "tweaking motor %s (pv=%s)" % (motor.name,motor.pvname)
  print "current position %s" % (motor.wm_string())
  if abs(direction) != 1:
    raise ValueError("direction needs to be +1 or -1")
  step = float(step)
  oldstep = 0
  k=keypress.KeyPress()
  while (k.isq() is False):
    if (oldstep != step):
      notice("stepsize: %f" % step)
      sys.stdout.flush()
      oldstep = step
    k.waitkey()
    if ( k.isu() ):
      step = step*2.
    elif ( k.isd() ):
      step = step/2.
    elif ( k.isr() ):
      motor.umvr(step*direction)
    elif ( k.isl() ):
      motor.umvr(-step*direction)
    elif ( k.iskey("g") ):
      print "enter absolute position (char to abort go to)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v.strip())
        motor.umv(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.iskey("s") ):
      print "enter new set value (char to abort setting)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v[0:-1])
        motor.set(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.isq() ):
      break
    else:
      print help_text
  print "final position: %s" % motor.wm_string()


def tweak_velo(motor,step=0.1):
  help_text = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
  help_text += "g = go abs, s = set"
  print "tweaking motor %s (pv=%s)" % (motor.name,motor.pvname)
  print "current speed %s" % (motor.get_speed())
  step = float(step)
  oldstep = 0
  k=keypress.KeyPress()
  while (k.isq() is False):
    if (oldstep != step):
      notice("stepsize: %f" % step)
      sys.stdout.flush()
      oldstep = step
    k.waitkey()
    if ( k.isu() ):
      step = step*2.
    elif ( k.isd() ):
      step = step/2.
    elif ( k.isr() ):
      motor.set_speed(motor.get_speed()+step)
      print "current speed %s" % (motor.get_speed())
    elif ( k.isl() ):
      motor.set_speed(motor.get_speed()-step)
      print "current speed %s" % (motor.get_speed())
    elif ( k.iskey("g") ):
      print "enter absolute speed (char to abort go to)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v.strip())
        motor.set_speed(v)
        print "current speed %s" % (motor.get_speed())
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.iskey("s") ):
      print "enter new set value (char to abort setting)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v[0:-1])
        motor.set(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.isq() ):
      break
    else:
      print help_text
  print "final speed: %s" % motor.get_speed()


def tweak2D(moth,motv,mothstep=0.1,motvstep=0.1,mothname=None,motvname=None,dirh=1,dirv=1):
  if mothname is None:
    mothname = moth.name
  if motvname is None:
    motvname = motv.name
  help_text ="left = moth neg dir; right = moth pos dir; up = motv pos dir, down = motv neg dir\n"
  help_text += "<shift>-down = motv-step/2; <shift>-up = step*2, <shift>-left = moth-step/2; <shift>-right = moth-step*2\n"
  help_text += "s: enter new stepsize\n"
  help_text += 'q = quit'
  print "current position (%s,%s) = (%s,%s)" % (mothname,motvname,moth.wm_string(),motv.wm_string())
  if abs(dirh) != 1 or abs(dirv) != 1:
    raise ValueError("direction needs to be +1 or -1")
  mothstep = float(mothstep)
  motvstep = float(motvstep)
  oldmothstep = 0
  oldmotvstep = 0
  k=keypress.KeyPress()
  while (k.isq() is False):
    if (oldmothstep != mothstep):
      print "%s stepsize: %g" % (mothname, mothstep)
      sys.stdout.flush()
      oldmothstep = mothstep
    if (oldmotvstep != motvstep):
      print "%s stepsize: %g" % (motvname, motvstep)
      sys.stdout.flush()
      oldmotvstep = motvstep
    k.waitkey()
    if ( k.issr() ):
      mothstep = mothstep*2.
    elif ( k.issl() ):
      mothstep = mothstep/2.
    elif ( k.isr() ):
      moth.umvr(mothstep*dirh,show_previous=False)
    elif ( k.isl() ):
      moth.umvr(-mothstep*dirh,show_previous=False)
    elif ( k.issu() ):
      motvstep = motvstep*2.
    elif ( k.issd() ):
      motvstep = motvstep/2.
    elif ( k.isu() ):
      motv.umvr(motvstep*dirv,show_previous=False)
    elif ( k.isd() ):
      motv.umvr(-motvstep*dirv,show_previous=False)
    elif ( k.iskey("s") ):
      v = raw_input("enter step size (one value for both horizontal and vertical)")
      try:
        v = float(v.strip())
        motvstep = v
        mothstep = v
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.isq() ):
      break
    else:
      print help_text


def tweak_mvr(motor,step=0.1,direction=1):
  help_text = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
  help_text += "g = go abs, s = set"
  print "tweaking motor %s (pv=%s)" % (motor.name,motor.pvname)
  print "current position %s" % (motor.wm_string())
  if abs(direction) != 1:
    raise ValueError("direction needs to be +1 or -1")
  step = float(step)
  oldstep = 0
  k=keypress.KeyPress()
  while (k.isq() is False):
    if (oldstep != step):
      nstr = "stepsize: %f" % step
      notice(nstr)
      sys.stdout.flush()
      oldstep = step
    k.waitkey()
    if ( k.isu() ):
      step = step*2.
    elif ( k.isd() ):
      step = step/2.
    elif ( k.isr() ):
      motor.umvr(step*direction,show_previous=False)
    elif ( k.isl() ):
      motor.umvr(-step*direction,show_previous=False)
    elif ( k.iskey("g") ):
      print "enter absolute position (char to abort go to)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v.strip())
        motor.umv(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.iskey("s") ):
      print "enter new set value (char to abort setting)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v[0:-1])
        motor.set(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.isq() ):
      break
    else:
      print help_text
  print "final position: %s" % motor.wm_string()


def dump_MMS_par(motor_pvlist):
  if (isinstance(motor_pvlist,str)):
    motor_pvlist = [motor_pvlist]
  pars = [
   'description'         , '.DESC',
   'acceleration'        , '.ACCL',
   'units (EGU)'         , '.EGU',
   'direction'           , '.DIR',
   'encoder step size'   , '.ERES',
   'Gear x Pitch'        , '.UREV',
   'User Offset (EGU)'   , '.OFF',
   'retry deadband (EGU)', '.RDBD',
   'Steps Per Rev'       , '.SREV',
   'Max speed (RPS)'     , '.SMAX',
   'Speed(RPS)'          , '.S',
   'Speed(UGU/S)'        , '.VELO',
   'base speed (RPS)'    , '.SBAS',
   'base speed (EGU/s)'  , '.VBAS',
   'backlash'            , '.BDST',
   'run current (%)'     , ':RC',
   'use encoder (:EE)'   , ':EE',
   'encoder lines per rev (:EL)'   , ':EL'
  ]
  fields_desc=pars[::2]
  fields=pars[1::2]
  out=[]
  title1="pvname"
  title2="------"
  for f in fields_desc:
    title1 += ",%s" % f
  for f in fields:
    title2 += ",%s" % f
  out.append(title1)
  out.append(title2)
  for m in motor_pvlist:
    v=m
    for f in fields:
      try:
        vv=Pv.get( m + f)
      except:
        print m + f
        vv="?"
      v += ",%s" % vv
    out.append(v)
  return out

def _dump_motorlist_tofile(file,motorlist):
  f=open(file,'wb')
  for line in motorlist:
    f.write(line+'\n')
  f.close()

def dump_MMS_par_tofile(motpvlist,filename):
  pl=dump_MMS_par(motpvlist)
  _dump_motorlist_tofile(filename,pl)
    
def load_MMS_pars(cvsfile,verbose=False):
  f=open(cvsfile)
  lines = f.readlines()
  for i in range(len(lines)): lines[i]=lines[i].rstrip("\n")
  fields = lines[1];
  lines = lines[2:];
  fields = fields.split(",")[1:]
  for l in lines:
    ll=l.split(",")
    pvbase=ll[0]
    if pvbase.startswith("#"): continue
    values=ll[1:]
    for i in range(len(fields)):
      f   = fields[i]
      pvw = pvbase + f
      pvr = pvw
      if (f == ":SET_RC"): pvr = pvbase + ":RC"
      if (f == ":SET_EE"): pvr = pvbase + ":EE"
      if f.startswith("#"): continue
      if (values[i] != "?"):
        try:
          vv=float(values[i])
        except:
          vv=values[i]
        if (f==":SET_RC"):  vv=str(values[i]); # for some reason the run current must be a string !
        if (f==":SET_EE"):  vv=str(values[i]); # for some reason the use encoder must be a string !
        if (f==".DIR"):  vv=int(values[i]);
        if (f==".SREV"): vv=int(values[i]);
        try:
          cv = Pv.get(pvr)
          if (verbose):
            print "current value ", cv
            print "setting  ",pvw," to ",values[i],
          if (f==".S"): Pv.put(pvbase+".SMAX",vv)
          Pv.put(pvw,vv)
          if (verbose): print " done"
        except pyca.pyexc:
          print "FAILED TO set ",pvw," to ",values[i]
        try:
          rv = Pv.get(pvr)
          if (verbose): print "readback ",pvr, "    " ,rv
        except pyca.pyexc:
          print "FAILED TO READBACK ",pvr
        if (rv != cv):
          print "!!!NOTE!!! The pv %s has changed from %s to %s" % (pvw,cv,rv)


def estimatedTimeNeededForMotion(deltaS,vBase,vFull,Acc):
  """ return the estimated time needed to complete a motion
      inputs:
         deltaS = how much is the motor going to move
         vBase  = starting speed (EGU/s)
         vFull  = full     speed (EGU/s)
         Acc    = acceleration   (EGU/s**2)"""
  deltaS = np.abs(deltaS)
  Acc = float(Acc)
  vFull = float(vFull)
  if (Acc == 0): #basespeed == full speed
    return deltaS/vFull
  timeFullSpeed = (deltaS-(vFull**2-vBase**2)/Acc)/vFull
  if (timeFullSpeed > 0):
    tTot = 2*(vFull-vBase)/Acc+timeFullSpeed
  else:
    tTot = 2*(np.sqrt(vBase**2+Acc*deltaS)-vBase)/Acc
  return tTot


def moveLinearInterpolated(pos,motMaster,motSlaves,calibrationPoints,moveIt=False):
  assert len(calibrationPoints)>1, "Need at least two calibration points"
  assert len(calibrationPoints)<3, "Calibration with more than 2 points is not yet supported"
  assert all(type(el) == str for el in calibrationPoints), "Calibration points need to be preset names (for now)"
  assert all( all(calibPoint in mot.presets.allPresets(doPrint=False).keys() for calibPoint in calibrationPoints) \
      for mot in motSlaves + [motMaster]), "Presets are not set for all motors required"

  fracmove = (pos - motMaster.presets.posVal(calibrationPoints[0]))/\
      (motMaster.presets.posVal(calibrationPoints[1])-motMaster.presets.posVal(calibrationPoints[0]))
  for mot in motSlaves + [motMaster]:
    position = (fracmove*\
    (mot.presets.posVal(calibrationPoints[1]) - mot.presets.posVal(calibrationPoints[0]))\
    + mot.presets.posVal(calibrationPoints[0]))
    if moveIt:
      mot.mv(position)
    else:
      print position


def slaveMotorOffsetsLinearInterpolated(motMaster,motSlaves,calibrationPoints):
  assert len(calibrationPoints)>1, "Need at least two calibration points"
  assert len(calibrationPoints)<3, "Calibration with more than 2 points is not yet supported"
  assert all(type(el) == str for el in calibrationPoints), "Calibration points need to be preset names (for now)"
  assert all( all(calibPoint in mot.presets.allPresets(doPrint=False).keys() for calibPoint in calibrationPoints) \
      for mot in motSlaves + [motMaster]), "Presets are not set for all motors required"
  pos = motMaster.wm()
  fracmove = (pos - motMaster.presets.posVal(calibrationPoints[0]))/\
      (motMaster.presets.posVal(calibrationPoints[1])-motMaster.presets.posVal(calibrationPoints[0]))
  slaveOffsets = []
  for mot in motSlaves:
    slaveOffsets.append(mot.wm() - (fracmove*\
    (mot.presets.posVal(calibrationPoints[1]) - mot.presets.posVal(calibrationPoints[0]))\
      - mot.presets.posVal(calibrationPoints[0])))
  return slaveOffsets


class translationOffRotationCenter(object):
  def __init__(mrot,mx,my,roffs=0,xoffs=0,yoffs=0):
    self.mrot = mrot
    self.mx = mx
    self.my = my
    self.xoffs = my
    self.yoffs = my
    self.roffs = my

  def calcxyforrot(r,xr,yr):
    x = np.sqrt(xr**2+yr**2) * np.sin(r-np.arctan(xr/yr)) - self.xoffs
    y = np.sqrt(xr**2+yr**2) * np.cos(r-np.arctan(xr/yr)) - self.yoffs
    return x,y

  def calcxryr(r,x,y):
    xr = (self.yoffs + y) * np.cos(r) + (self.xoffs + x) * np.sin(r)
    yr = (self.yoffs + y) * np.sin(r) + (self.xoffs + x) * np.cos(r)


class rotatedMotorPair(object):
  #mot X and Y are actual motors, theta is the angle to the coordinate system they should move in.
  def __init__(self, motX, motY, theta, originX=0, originY=0):
    self.motX = motX
    self.motY = motY
    self.setTheta(theta)
    #origin not used yet!
    self.originX=originX
    self.originY=originY

  def setOrigin(X,Y):
    self.originX=X
    self.originY=Y

  def setTheta(self, theta):
    self.theta = 2.*np.pi*theta/360.
    self.rot = np.array([[np.cos(self.theta), np.sin(self.theta)],[-np.sin(self.theta), np.cos(self.theta)]])
    self.rotM = np.array([[np.cos(self.theta), -np.sin(self.theta)],[np.sin(self.theta), np.cos(self.theta)]])

  def getTheta(self):
    return self.theta/2./np.pi*360.

  def wait(self):
    self.motX.wait()
    self.motY.wait()

  def newCoord(self, X, Y):
    return np.dot(np.array([X,Y]),self.rot)

  def motCoord(self, Xp, Yp):
    return np.dot(np.array([Xp,Yp]),self.rotM)

  def setN(self, value):
    motCoord = self.motCoord(value,self.getP())
    print self.motX.wm(), self.motX.wm()
    print motCoord
    self.motX.mv(motCoord[0])
    self.motY.mv(motCoord[1])
    print self.motX.wm(), self.motX.wm()

  def setP(self, value):
    motCoord = self.motCoord(self.getN(),value)
    self.motX.mv(motCoord[0])
    self.motY.mv(motCoord[1])

  def getN(self):
    newCoord = self.newCoord(self.motX.wm(), self.motY.wm())
    return newCoord[0]

  def getP(self):
    newCoord = self.newCoord(self.motX.wm(), self.motY.wm())
    return newCoord[1]


