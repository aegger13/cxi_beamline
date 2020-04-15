# This module provides support
# for the Large Offset Dual Crystal monochromators
# located at XPP & XCS/XRT
# 
# Author:         Marco Cammarata (SLAC)
# Created:        Aug 27, 2010
# Modifications:
#   Aug 27, 2010 MC
#       first version
#   Sep 23, 2015 DF
#       merge XCS/XPP diffs

from numpy import rad2deg, deg2rad, arcsin, sqrt, tan, sin, cos, pi
import sys
from blutil import estr
import psp.Pv as Pv
from blbase import virtualmotor
from blbase.stateioc import stateiocDevice
from blutil.calc import tand, BraggAngle, dSpace, lam2E


class LOM:
  """
  Class to control the LODCM (Large Offset Dual Crystal Monochromator) instruments
  located at XPP and XCS/XRT
  """
  def __init__(self,z1,x1,y1,th1,ch1,h1n,h1p,th1f,ch1f,z2,x2,y2,th2,ch2,h2n,diode2,th2f,ch2f,dh,dv,dr,df,dd,yag_zoom,objName="lom",pvBase=None,moveX1=True,motors=None):
    #self.E = None
    #self.E1 = None
    #self.E2 = None
    self._cmd=Pv.Pv('%s:CMD'%pvBase, monitor=True)
    self._cmd.set_string_enum(True)
    self.objName = objName
    self.pvBase = pvBase
    self._moveX1 = moveX1
    self._motors = motors

    self._stateh1n=stateiocDevice('%s:H1N'%pvBase)
    if self._moveX1:
      self._statex1=stateiocDevice('%s:X1'%pvBase)
    self._statey1=stateiocDevice('%s:Y1'%pvBase)
    self._statechi1=stateiocDevice('%s:CHI1'%pvBase)
    self._stateh2n=stateiocDevice('%s:H2N'%pvBase)
    self._statey2=stateiocDevice('%s:Y2'%pvBase)
    self._statechi2=stateiocDevice('%s:CHI2'%pvBase)
    self._statediode=stateiocDevice('%s:DIODE'%pvBase)
    self._statediagvert=stateiocDevice('%s:DV'%pvBase)
    self._statediaghoriz=stateiocDevice('%s:DH'%pvBase)
    self._statefoils=stateiocDevice('%s:FOIL'%pvBase)

    self.z1 = z1
    self.x1 = x1
    self.y1 = y1
    self.th1 = th1
    self.chi1 = ch1
    self.h1n = h1n
    self.h1p = h1p
    self.th1f = th1f
    self.chi1f = ch1f

    self.z2 = z2
    self.x2 = x2
    self.y2 = y2
    self.th2 = th2
    self.chi2 = ch2
    self.h2n = h2n
    self.diode2 = diode2
    self.th2f = th2f
    self.chi2f = ch2f

    self.dh   = dh
    self.dv   = dv
    self.dr   = dr
    self.df   = df
    self.dd   = dd
    self.yag_zoom   = yag_zoom

    self.tower1motors = {
      "x1": self.x1,
      "y1": self.y1,
      "z1": self.z1,
      "th1": self.th1,
      "chi1": self.chi1,
      "h1n": self.h1n,
      "h1p": self.h1p,
      "th1f": self.th1f,
      "chi1f": self.chi1f
    }

    self.tower2motors = {
      "x2": self.x2,
      "y2": self.y2,
      "z2": self.z2,
      "th2": self.th2,
      "chi2": self.chi2,
      "h2n": self.h2n,
      "diode2": self.diode2,
      "th2f": self.th2f,
      "chi2f": self.chi2f
    }

    self.tower3motors = {
      "dh": self.dh,
      "dv": self.dv,
      "dr": self.dr,
      "df": self.df,
      "dd": self.dd,
      "yag_zoom": self.yag_zoom
    }

    # Create virtual motors for C and Si using offset PVs 
    if pvBase is not None:
      self.th1C = self._create_crystal_vm('lom_th1C', self.th1, 'TH1:OFF_C')
      self.th2C = self._create_crystal_vm('lom_th2C', self.th2, 'TH2:OFF_C')
      self.z1C = self._create_crystal_vm('lom_z1C', self.z1, 'Z1:OFF_C')
      self.z2C = self._create_crystal_vm('lom_z2C', self.z2, 'Z2:OFF_C')
      self.x1C = self._create_crystal_vm('lom_x1C', self.x1, 'X1:OFF_C')
      self.x2C = self._create_crystal_vm('lom_x2C', self.x2, 'X2:OFF_C')
      self.y1C = self._create_crystal_vm('lom_y1C', self.y1, 'Y1:OFF_C', use_ims_preset=True)
      self.y2C = self._create_crystal_vm('lom_y2C', self.y2, 'Y2:OFF_C', use_ims_preset=True)
      self.chi1C = self._create_crystal_vm('lom_chi1C', self.chi1, 'CHI1:OFF_C', use_ims_preset=True)
      self.chi2C = self._create_crystal_vm('lom_chi2C', self.chi2, 'CHI2:OFF_C', use_ims_preset=True)
      self.h1nC = self._create_crystal_vm('lom_h1nC', self.h1n, 'H1N:OFF_C', use_ims_preset=True)
      self.h1pC = self._create_crystal_vm('lom_h1pC', self.h1p, 'H1P:OFF_C')
      self.h2nC = self._create_crystal_vm('lom_h2nC', self.h2n, 'H2N:OFF_C', use_ims_preset=True)
      self.th1Si = self._create_crystal_vm('lom_th1Si', self.th1, 'TH1:OFF_Si')
      self.th2Si = self._create_crystal_vm('lom_th2Si', self.th2, 'TH2:OFF_Si')
      self.z1Si = self._create_crystal_vm('lom_z1Si', self.z1, 'Z1:OFF_Si')
      self.z2Si = self._create_crystal_vm('lom_z2Si', self.z2, 'Z2:OFF_Si')
      self.x1Si = self._create_crystal_vm('lom_x1Si', self.x1, 'X1:OFF_Si')
      self.x2Si = self._create_crystal_vm('lom_x2Si', self.x2, 'X2:OFF_Si')
      self.y1Si = self._create_crystal_vm('lom_y1Si', self.y1, 'Y1:OFF_Si', use_ims_preset=True)
      self.y2Si = self._create_crystal_vm('lom_y2Si', self.y2, 'Y2:OFF_Si', use_ims_preset=True)
      self.chi1Si = self._create_crystal_vm('lom_chi1Si', self.chi1, 'CHI1:OFF_Si', use_ims_preset=True)
      self.chi2Si = self._create_crystal_vm('lom_chi2Si', self.chi2, 'CHI2:OFF_Si', use_ims_preset=True)
      self.h1nSi = self._create_crystal_vm('lom_h1nSi', self.h1n, 'H1N:OFF_Si', use_ims_preset=True)
      self.h1pSi = self._create_crystal_vm('lom_h1pSi', self.h1p, 'H1P:OFF_Si')
      self.h2nSi = self._create_crystal_vm('lom_h2nSi', self.h2n, 'H2N:OFF_Si', use_ims_preset=True)
    # Create virtual motors for tweaking the lodcm energy
    self.E1           = virtualmotor.VirtualMotor("lomE1",self.moveE1,self.getE1,self.waitE,self.setE1,motorsobj=self._motors)
    self.E1tweak      = virtualmotor.VirtualMotor("lomE1tweak",self.moveE1tweak, self.getE1,self.waitE1tweak,self.setE1,motorsobj=self._motors)
    self.E1C          = virtualmotor.VirtualMotor("lomE1C",self.moveE1C, self.getE1C,self.waitE,self.setE1C,motorsobj=self._motors)
    self.E1Si         = virtualmotor.VirtualMotor("lomE1Si",self.moveE1Si, self.getE1Si,self.waitE,self.setE1Si,motorsobj=self._motors)
    self.E            = virtualmotor.VirtualMotor("lomE",self.moveE,self.getE,self.waitE,self.setE,motorsobj=self._motors)
    self.Etweak       = virtualmotor.VirtualMotor("lomEtweak",self.moveEtweak,self.getE,self.waitE,self.setE,motorsobj=self._motors)
    self.EC           = virtualmotor.VirtualMotor("lomEC", self.moveEC, self.getEC, self.waitE, self.setEC,motorsobj=self._motors)
    self.ECtweak      = virtualmotor.VirtualMotor("lomECtweak", self.moveECtweak, self.getEC, self.waitE, self.setEC,motorsobj=self._motors)
    self.ESi          = virtualmotor.VirtualMotor("lomESi", self.moveESi, self.getESi, self.waitE, self.setESi,motorsobj=self._motors)
    self.ESitweak     = virtualmotor.VirtualMotor("lomESitweak", self.moveESitweak, self.getESi, self.waitE, self.setESi,motorsobj=self._motors)
    self.E1Si333      = virtualmotor.VirtualMotor("lomE1Si333",self.moveE1Si333, self.getE1Si333,self.waitE,self.setE1Si333,motorsobj=self._motors)
    self.ESi333       = virtualmotor.VirtualMotor("lomESi333", self.moveESi333, self.getESi333, self.waitE, self.setESi333,motorsobj=self._motors)
    self.ESi333tweak  = virtualmotor.VirtualMotor("lomESi333tweak", self.moveESi333tweak, self.getESi333, self.waitE, self.setESi333,motorsobj=self._motors)
    # Create vernier vm
    self.ESitweakVernier = self._create_vernier_vm("lomESitweakVernier")

  @property
  def mode(self):
    """ last commanded mode of the lodcm """
    if not self._cmd.ismonitored:
      self._cmd.monitor_start()
    return self._cmd.value

  def _is_t1_c(self):
    return (self._stateh1n.is_c() or self._stateh1n.is_out()) and self._statey1.is_c() and self._statechi1.is_c()

  def _is_t1_si(self):
    return (self._stateh1n.is_si() or self._stateh1n.is_out()) and self._statey1.is_si() and self._statechi1.is_si()

  def _is_t2_c(self):
    return self._stateh2n.is_c() and self._statey2.is_c() and self._statechi2.is_c()

  def _is_t2_si(self):
    return self._stateh2n.is_si() and self._statey2.is_si() and self._statechi2.is_si()

  def _get_relection(self, n, astuple, check):
    refs = None
    ref = None
    if n==1:
      if self._is_t1_c():
        refs = Pv.get('%s:T1C:REF'%self.pvBase)
      elif self._is_t1_si():
        refs = Pv.get('%s:T1Si:REF'%self.pvBase)
    elif n==2:
      if self._is_t2_c():
        refs = Pv.get('%s:T1C:REF'%self.pvBase)
      elif self._is_t2_si():
        refs = Pv.get('%s:T1Si:REF'%self.pvBase)
    if check and refs is None:
      raise ValueError("Unable to determine crystal reflection")
    if astuple:
      return refs
    else:
      if refs is not None:
        for r in refs:
          if ref is None:
            ref = str(r)
          else:
            ref += str(r)
      return ref

  def _get_material(self, n, check):
    if n==1:
      if self._is_t1_c():
        return 'C'
      elif self._is_t1_si():
        return 'Si'
    elif n==2:
      if self._is_t2_c():
        return 'C'  
      elif self._is_t2_si():
        return 'Si'
    if check:
      raise ValueError("Unable to determine crystal material")

  def get_t1_reflection(self, astuple=False, check=False):
    return self._get_relection(1, astuple, check)

  def get_t2_reflection(self, astuple=False, check=False):
    return self._get_relection(2, astuple, check)

  def get_reflection(self, astuple=False, check=False):
    r1 = self.get_t1_reflection(astuple, check)
    r2 = self.get_t2_reflection(astuple, check)
    if (r1 != r2):
      print "\nWARNING:  Crystals not matched (c1='%s', c2='%s')\n" % (r1, r2)
      raise ValueError("Invalid Crystal Arrangement")
    return r1

  def get_t1_material(self, check=False):
    return self._get_material(1, check)

  def get_t2_material(self, check=False):
    return self._get_material(2, check)

  def get_material(self, check=False):
    m1 = self.get_t1_material(check)
    m2 = self.get_t2_material(check)
    if (m1 != m2):
      print "\nWARNING:  Crystals not matched (c1='%s', c2='%s')\n" % (m1, m2)
      raise ValueError("Invalid Crystal Arrangement")
    return m1

  def get_t1_type(self):
    mat = self.get_t1_material()
    ref = self.get_t1_reflection()
    if mat is None or ref is None:
      return "Unknown"
    else:
      return "%s '%s'"%(mat, ref)

  def get_t2_type(self):
    mat = self.get_t2_material()
    ref = self.get_t2_reflection()
    if mat is None or ref is None:
      return "Unknown"
    else:
      return "%s '%s'"%(mat, ref)

  def __repr__(self):
    try:
      return self.status()
    except:
      print "LODCM: cannot print status (python exception)"
      return ""

  def status(self):
    mat1 = self._get_material(1, check=False)
    mat2 = self._get_material(2, check=False)
    mat = mat1 or mat2

    str  = self.info(toprint=0)
    str += "\n"
    if mat == "Si":
      str += self.si_status(toprint=False)
      str += "\n"
    elif mat == "C":
      str += self.c_status(toprint=False)
      str += "\n"
    try:
      str += self.tower1(toprint=0)
      str += "\n"
    except:
      print "error in tower1 status"
    try:
      str += self.tower2(toprint=0)
      str += "\n"
    except:
      print "error in tower2 status"
    try:
      str += self.tower3(toprint=0)
    except:
      print "error in tower3 status"
    return str

  def _create_crystal_vm(self, name, motor, offset_pv, use_ims_preset=False):
    offset_pv = '%s:%s'%(self.pvBase, offset_pv)
    def move(pos):
      motor.mv(pos+Pv.get(offset_pv))
    def wm():
      return motor.wm() - Pv.get(offset_pv)
    def set(value):
      if use_ims_preset:
        Pv.put('%s_SET'%offset_pv, motor.wm()-value)
      Pv.put(offset_pv, motor.wm()-value)
    return virtualmotor.VirtualMotor(name, move, wm, set=set, motorsobj=self._motors)

  def _create_vernier_vm(self, name):
    def moveESitweakVernier(E):
      self.ESitweak.mv(E)
      self._motors.vernier(E)
    def waitESitweakVernier():
      sleep(5)
    return virtualmotor.VirtualMotor(name, moveESitweakVernier, self.getESi, waitESitweakVernier, motorsobj=self._motors)

  def _put_crystal_preset(self, mot, crystal, value):
    Pv.put('%s:%s:OFF_%s_SET'%(self.pvBase, mot, crystal), value)

  def info(self,toprint=1):
    pre= "%s - " % estr("IN",type="normal")
    space=" "*3
    str = estr("LODCM Status\n", color="white", type="bold")
    if self._moveX1:
      x1out = self._statex1.is_out()
      x1in = self._statex1.is_in()
    else:
      x1out = True
      x1in = True
    if self._stateh1n.is_out() and x1out:
      str += "crystal 1 is %s\n" % estr("OUT",color='green')
    elif (self._stateh1n.is_c() or self._stateh1n.is_si()) and x1in:
      str += "crystal 1 is %s\n" % estr("IN",type="normal")
    else:
      str += "crystal 1 is %s\n" % estr("Unknown position",color='red') 

    str += "%s1st crystal type: %s\n" % (space, self.get_t1_type())
    str += "%s2nd crystal type: %s\n" % (space, self.get_t2_type())

    try:
      str += "%sEnergy 1st crystal = \t %.4f keV\n" % (space,self.getE1())
    except Exception, exc:
      str += "%sEnergy 1st crystal is Unknown. %s\n" % (space,exc)
    try:
      str += "%sEnergy 2nd crystal = \t %.4f keV\n" % (space,self.getE2())
    except Exception, exc:
      str += "%sEnergy 2nd crystal is Unknown. %s\n" % (space,exc) 

    # Check for horizontal elements on the diagnostic tower
    if self._statediaghoriz.is_out() or self._statediaghoriz.is_outlow():
       str+= "%sHorizontal elements status:\t %s\n" % (space,estr("OUT",color="green"))
    else:
       str+= "%sHorizontal elements status:\t " % space
       if self._statediaghoriz.is_dectris():
         str+=pre
         str += "Dectris \n"
       elif self._statediaghoriz.is_slit1(): 
         str+=pre
         str += "Slit 1 (100 micron)\n"
       elif self._statediaghoriz.is_slit2():
         str+=pre
         str += "Slit 2 (500 micron) \n"
       elif self._statediaghoriz.is_slit3():
         str+=pre
         str += "Slit 3 (1 mm) \n"
       else:
         str += "%s\n" % estr("Unkown position",type="normal")
# Check for vertical elements on the diagnostic tower
    if self._statediagvert.is_out():
       str+= "%sVertical elements status:\t %s\n" % (space,estr("OUT",color="green"))
    else:
       str+= "%sVertical elements status:\t "  % space
       if self._statediagvert.is_yag():
         str+=pre
         str += "Yag-mono \n"
       elif self._statediagvert.is_slit1(): 
         str+=pre
         str += "Slit 1 (100 micron) \n"
       elif self._statediagvert.is_slit2(): 
         str+=pre
         str += "Slit 2 (500 micron) \n"
       elif self._statediagvert.is_slit3(): 
         str+=pre
         str += "Slit 3 (1 mm) \n"
       else:
         str += "%s\n" % estr("Unkown position",type="normal")
#Check for calibration foils    
    foils=self._statefoils.statesAll()
    foil=self._statefoils.state()
    if self._statefoils.is_out():
      str+= "%sCalibration foils status:\t %s\n%s" % (space,estr("OUT",color="green"),space)
    elif foil in foils:
      str+= "%sCalibration foils status:\t %s - %s\n%s" % (space,estr("IN",type="normal"),foil,space)
    else:
      str+= "%sCalibration foils status:\t %s\n%s" % (space,estr("Unknown position",type="normal"),space)
    if self._statediode.is_out():
       str+= "Diode 1 status:\t\t %s\n" % (estr("OUT",color="green"))
    elif self._statediode.is_in():
       str+= "Diode 1 status:\t\t %s\n" % (estr("IN",type="normal"))
    else:
       str+= "Diode 1 status:\t\t %s\n" % (estr("Unknown position",type="normal"))
    if toprint:
      print str
    else:
      return str

  def tower1(self,toprint=1):
    str  = "** Tower 1 (crystal 1) **\n"
    str += "  (x,y,z,hn,hp)   [user]: %+7.3f,%+7.3f,%+9.3f,%+7.3f,%+.3f\n" % (self.x1.wm(),self.y1.wm(),self.z1.wm(),self.h1n.wm(),self.h1p.wm())
    str += "  (x,y,z,hn,hp)   [dial]: %+7.3f,%+7.3f,%+9.3f,%+7.3f,%+.3f\n" % (self.x1.wm_dial(),self.y1.wm_dial(),self.z1.wm_dial(),self.h1n.wm_dial(),self.h1p.wm_dial())
    str += "  (x,y,z,hn,hp) [offset]: %+7.3f,%+7.3f,%+9.3f,%+7.3f,%+.3f\n" % (self.x1.wm_offset(),self.y1.wm_offset(),self.z1.wm_offset(),self.h1n.wm_offset(),self.h1p.wm_offset())
    str += "  (th,ch,thf,chf)   [user]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th1.wm(),self.chi1.wm(),self.th1f.wm(),self.chi1f.wm())
    str += "  (th,ch,thf,chf)   [dial]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th1.wm_dial(),self.chi1.wm_dial(),self.th1f.wm_dial(),self.chi1f.wm_dial())
    str += "  (th,ch,thf,chf) [offset]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th1.wm_offset(),self.chi1.wm_offset(),self.th1f.wm_offset(),self.chi1f.wm_offset())
    if (toprint):
      print str
    else:
      return str

  def tower2(self,toprint=1):
    str = "** Tower 2 (crystal 2) **\n"
    str += "  (x,y,z,hn)   [user]: %+7.3f,%+7.3f,%+9.3f,%+7.3f\n" % (self.x2.wm(),self.y2.wm(),self.z2.wm(),self.h2n.wm())
    str += "  (x,y,z,hn)   [dial]: %+7.3f,%+7.3f,%+9.3f,%+7.3f\n" % (self.x2.wm_dial(),self.y2.wm_dial(),self.z2.wm_dial(),self.h2n.wm_dial())
    str += "  (x,y,z,hn) [offset]: %+7.3f,%+7.3f,%+9.3f,%+7.3f\n" % (self.x2.wm_offset(),self.y2.wm_offset(),self.z2.wm_offset(),self.h2n.wm_offset())
    str += "  (th,ch,thf,chf)   [user]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th2.wm(),self.chi2.wm(),self.th2f.wm(),self.chi2f.wm())
    str += "  (th,ch,thf,chf)   [dial]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th2.wm_dial(),self.chi2.wm_dial(),self.th2f.wm_dial(),self.chi2f.wm_dial())
    str += "  (th,ch,thf,chf) [offset]: %+8.4f,%+8.4f,%+8.4f,%+8.4f\n" % (self.th2.wm_offset(),self.chi2.wm_offset(),self.th2f.wm_offset(),self.chi2f.wm_offset())
    if (toprint):
      print str
    else:
      return str

  def tower3(self,toprint=1):
    str = "** Tower 3 (diagnostic) **\n"
    str += "  (h,v,r)   [user]: %+7.2f,%+7.2f,%+7.2f\n" % (self.dh.wm(),self.dv.wm(),self.dr.wm())
    str += "  (h,v,r)   [dial]: %+7.2f,%+7.2f,%+7.2f\n" % (self.dh.wm_dial(),self.dv.wm_dial(),self.dr.wm_dial())
    str += "  (h,v,r) [offset]: %+7.2f,%+7.2f,%+7.2f\n" % (self.dh.wm_offset(),self.dv.wm_offset(),self.dr.wm_offset())
    str += "  (pips,filter)   [user]: %+7.2f,%+7.2f\n" % (self.dd.wm(),self.df.wm())
    str += "  (pips,filter)   [dial]: %+7.2f,%+7.2f\n" % (self.dd.wm_dial(),self.df.wm_dial())
    str += "  (pips,filter) [offset]: %+7.2f,%+7.2f\n" % (self.dd.wm_offset(),self.df.wm_offset())
    if (toprint):
      print str
    else:
      return str

  def _vmot_status(self, n, crystal):
    rows = (("x{0}{1}", "y{0}{1}", "z{0}{1}"),
            ("h{0}n{1}", "h{0}p{1}"),
            ("th{0}{1}", "chi{0}{1}"))
    txt = ""
    for labels in rows:
      labels = [ lab.format(n, crystal) for lab in labels ]
      labels = [ lab for lab in labels if hasattr(self, lab) ]
      pos = [ "{0:9.3f}".format(getattr(self, lab).wm()) for lab in labels ]
      txt += "  {0:18} {1}\n".format("(" + ",".join(labels) + "):", ",".join(pos))
    return txt

  def si_status(self,toprint=True):
    txt = "** Si Position Status (0 is normal set position) **\n"
    txt += self.si1_status(toprint=False)
    txt += self.si2_status(toprint=False)
    if toprint:
      print txt
    else:
      return txt

  def si1_status(self,toprint=True):
    txt = self._vmot_status(1, "Si")
    if toprint:
      print txt
    else:
      return txt 

  def si2_status(self,toprint=True):
    txt = self._vmot_status(2, "Si")
    if toprint:
      print txt
    else:
      return txt

  def c_status(self,toprint=True):
    txt = "** C Position Status (0 is normal set position) **\n"
    txt += self.c1_status(toprint=False)
    txt += self.c2_status(toprint=False)
    if toprint:
      print txt
    else:
      return txt

  def c1_status(self,toprint=True):
    txt = self._vmot_status(1, "C")
    if toprint:
      print txt
    else:
      return txt

  def c2_status(self,toprint=True):
    txt = self._vmot_status(2, "C")
    if toprint:
      print txt
    else:
      return txt

  def set_inpos(self,inx1):
    if self._moveX1:
      self._statex1.setPos_in(inx1)
  def set_outpos(self,outh1n,outx1):
    if self._moveX1:
      self._statex1.setPos_out(outx1)
    self._stateh1n.setPos_out(outh1n)
  def set_diode_inpos(self,indiode):
    self._statediode.setPos_in(indiode)
  def set_diode_outpos(self,outdiode):
    self._statediode.setPos_out(outdiode)
  def set_vertical_outpos(self,outvert):
    self._statediagvert.setPos_out(outvert)
  def set_horizontal_outpos(self,outhoriz):
    self._statediaghoriz.setPos_out(outhoriz)
  def set_horizontal_outlowpos(self,outlowhoriz):
    self._statediaghoriz.setPos_outlow(outlowhoriz)
  def set_dectris_inpos(self,indectris):
    self._statediaghoriz.setPos_dectris(indectris)
  def set_yag_inpos(self,inyag):
    self._statediagvert.setPos_yag(inyag)
  def set_yag_outpos(self,outyag):
    self._statediagvert.setPos_out(outyag)
  def set_vslit_pos(self,n,vslit_pos):
    if (n>0)&(n<4):
      if n==1:
        self._statediagvert.setPos_slit1(vslit_pos)
        print "100 micron slit inpos set to", vslit_pos
      if n==2:
        self._statediagvert.setPos_slit2(vslit_pos)
        print "500 micron slit inpos set to", vslit_pos
      if n==3:
        self._statediagvert.setPos_slit3(vslit_pos)
        print "2 mm slit inpos set to", vslit_pos
    else:
       print "allowed 1-3"
  def set_hslit_pos(self,n,hslit_pos):
    if (n>0)&(n<4):
      if n==1:
        self._statediaghoriz.setPos_slit1(hslit_pos)
        print "100 micron slit inpos set to", hslit_pos
      if n==2:
        self._statediaghoriz.setPos_slit2(hslit_pos)
        print "500 micron slit inpos set to", hslit_pos
      if n==3:
        self._statediaghoriz.setPos_slit3(hslit_pos)
        print "2 mm slit inpos set to", hslit_pos
    else:
       print "allowed 1-3"
  def set_foils_pos(self,n,foils_pos):
    if (n>=0)&(n<8):
      state = self._statefoils.statesAll()[n]
      move_func = getattr(self._statefoils, 'setPos_%s'%(state.lower()))
      move_func(foils_pos)
      print state, "foil inpos set to", foils_pos
    else:
       print "allowed 0-7"

  def set_Si_y1(self, Si_y1):
    self._put_crystal_preset('Y1', 'Si', Si_y1)
  def set_Si_y2(self, Si_y2):
    self._put_crystal_preset('Y2', 'Si', Si_y2)
  def set_Si_h1n(self, Si_h1n):
    self._put_crystal_preset('H1N', 'Si', Si_h1n)
  def set_Si_h2n(self, Si_h2n):
    self._put_crystal_preset('H2N', 'Si', Si_h2n)
  def set_Si_chi1(self, Si_chi1):
    self._put_crystal_preset('CHI1', 'Si', Si_chi1)
  def set_Si_chi2(self, Si_chi2):
    self._put_crystal_preset('CHI2', 'Si', Si_chi2)

  def set_C_y1(self, C_y1):
    self._put_crystal_preset('Y1', 'C', C_y1)
  def set_C_y2(self, C_y2):
    self._put_crystal_preset('Y2', 'C', C_y2)
  def set_C_h1n(self, C_h1n):
    self._put_crystal_preset('H1N', 'C', C_h1n)
  def set_C_h2n(self, C_h2n):
    self._put_crystal_preset('H2N', 'C', C_h2n)
  def set_C_chi1(self, C_chi1):
    self._put_crystal_preset('CHI1', 'C', C_chi1)
  def set_C_chi2(self, C_chi2):
    self._put_crystal_preset('CHI2', 'C', C_chi2)

  # moving to Si
  def SiIN(self,all=False):
    print('moving to Si ...\n')
    motornames = ['y1','y2','h1n','h2n','chi1','chi2']
    for mot in motornames:
      try:
        if mot=='h1n' and not all: continue
        self.__dict__[mot+'Si'].mv(0)
      except:
        print '%s motion failed ...\n' % mot
    if self._moveX1 and all:
      self._statex1.move_in()
    self._cmd.put('Si')

  # move to diamond
  def diamondIN(self,all=False):
    print('moving to diamond ...\n')
    motornames = ['y1','y2','h1n','h2n','chi1','chi2']
    for mot in motornames:
      try:
        if mot=='h1n' and not all: continue
        self.__dict__[mot+'C'].mv(0)
      except:
        print '%s motion failed ...\n' % mot
    if self._moveX1 and all:
      self._statex1.move_in()
    self._cmd.put('C')
  
  def moveout(self):
    self._stateh1n.move_out()
    if self._moveX1:
      self._statex1.move_out()
  def movein(self, ID=None):
    if ID is None:
      ID = self.mode
    if ID == 'Si':
      if self._moveX1:
        self._statex1.move_in()
      self._stateh1n.move_si()
      self._cmd.put(ID)
    elif ID == 'C':
      if self._moveX1:
        self._statex1.move_in()
      self._stateh1n.move_c()
      self._cmd.put(ID)
    else:
      raise ValueError('Invalid ID type: %s'%ID)
  def diodein(self):
    self._statediode.move_in()
  def diodeout(self):
    self._statediode.move_out()
  def verticalout(self):
    self._statediagvert.move_out()
  def yagin(self):
    self._statediagvert.move_yag()
  def yagout(self):
    self._statediagvert.move_out()
  def vslitin(self,n):
    if (n>0)&(n<4):
      if n==1:
        self._statediagvert.move_slit1()
        print "100 micron slit in" 
      if n==2:
        self._statediagvert.move_slit2()
        print "500 micron slit in" 
      if n==3:
        self._statediagvert.move_slit3()
        print "2 mm slit in" 
    else:
       print "allowed 1-3"
  def horizontalout(self):
    self._statediaghoriz.move_out()
  def horizontaloutlow(self):
    self._statediaghoriz.move_outlow()
  def dectrisin(self):
    self._statediaghoriz.move_dectris()
  def hslitin(self,n):
    if (n>0)&(n<4):
      if n==1:
        self._statediaghoriz.move_slit1()
        print "100 micron slit in" 
      if n==2:
        self._statediaghoriz.move_slit2()
        print "500 micron slit in"
      if n==3:
        self._statediaghoriz.move_slit3()
        print "2 mm slit in" 
    else:
      print "allowed 1-3"
  def foilsout(self):
    self._statefoils.move_out()
  def foilsin(self,n):
    if (n>0)&(n<8):
      state = self._statefoils.statesAll()[n]
      move_func = getattr(self._statefoils, 'move_%s'%(state.lower()))
      move_func()
      print state, "foil in"
    else:
       print "allowed 1-7"

  ### Si(111) motions
  ## calculate the geometry
  def getLomGeom(self, E, ID, reflection):
    th = BraggAngle(ID, reflection, E)*pi/180
    zm = 300/tan(2*th)
    thm=rad2deg(th)
    return thm, zm

  ## LOM E1 ##
  def moveE1(self,E,ID=None,reflection=None,tweak=False):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_t1_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_t1_material(check=True)
    (th,z) = self.getLomGeom(E,ID,reflection)
    if ID=='Si':
      self.th1Si.move_silent(th)
      if not tweak:
        self.dr.move_silent(2*th)
      self.z1Si.move_silent(-z)
    elif ID=='C':
      self.th1C.move_silent(th)
      if not tweak:
        self.dr.move_silent(2*th)
      self.z1C.move_silent(-z)
    else:
      raise ValueError('Invalid material ID: %s'%ID)

  def getE1(self, ID=None, reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_t1_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_t1_material(check=True)
    if ID=='Si':
      th = self.th1Si.wm()
    elif ID=='C':
      th = self.th1C.wm()
    else:
      raise ValueError('Invalid material ID: %s'%ID)
    l  = 2*sin(deg2rad(th))*dSpace(ID, reflection)
    return lam2E(l)/1000

  def waitE1(self):
    self.th1.wait()
    self.dr.wait()
    self.z1.wait()
  
  def moveE1tweak(self,E,ID=None,reflection=None):
    self.moveE1(E,ID,reflection,tweak=True)

  def waitE1tweak(self):
    self.th1.wait()
    self.z1.wait()

  ## LOM E2  ##
  def moveE2(self,E,ID=None,reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_t2_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_t2_material(check=True)
    (th,z) = self.getLomGeom(E,ID,reflection)
    if ID=='Si':
      self.th2Si.move_silent(th)
      self.z2Si.move_silent(z)
    elif ID=='C':
      self.th2C.move_silent(th)
      self.z2C.move_silent(z)
    else:
      raise ValueError('Invalid material ID: %s'%ID)

  def getE2(self,ID=None,reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_t2_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_t2_material(check=True)
    if ID=='Si':
      th = self.th2Si.wm()
    elif ID=='C':
      th = self.th2C.wm()
    else:
      raise ValueError('Invalid material ID: %s'%ID)
    #th = self.th2.wm()
    l  = 2*sin(deg2rad(th)) *dSpace(ID,reflection)
    return lam2E(l)/1000

  def waitE2(self):
    self.th2.wait()
    self.z2.wait()

  ## LOM E
  def moveE(self,E,ID=None, reflection=None,tweak=False):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    (th,z) = self.getLomGeom(E,ID,reflection)
    if ID=='Si':
      self.th1Si.move_silent(th)
      self.th2Si.move_silent(th)
      if not tweak:
        self.dr.move_silent(2*th)
      self.z1Si.move_silent(-z)
      self.z2Si.move_silent(z)
    elif ID=='C':
      self.th1C.move_silent(th)
      self.th2C.move_silent(th)
      if not tweak:
        self.dr.move_silent(2*th)
      self.z1C.move_silent(-z)
      self.z2C.move_silent(z)
    else:
      raise ValueError('Invalid material ID: %s'%ID)
  
  def moveEtweak(self,E,ID=None, reflection=None):
    self.moveE(E,ID,reflection,tweak=True)

  def getE(self, ID=None, reflection=None):
    return self.getE1(ID, reflection) # since energy is determined by the first crystal.

  def waitE(self):
    self.th1.wait()
    self.th2.wait()
    self.dr.wait()
    self.z1.wait()
    self.z2.wait()

  def tweakX(self,x,ID=None):
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    if ID=='Si':
      th = self.th2Si.wm()
    elif ID=='C':
      th = self.th2C.wm()
    else:
      raise ValueError('Invalid material ID: %s'%ID)
    z = x/tand(2*th)
    start_x = self.x2.wm()
    start_z = self.z2.wm()
    self.x2.move_relative(x)
    self.z2.move_relative(z)
    self.x2.wait()
    self.z2.wait()
    end_x = self.x2.wm()
    end_z = self.z2.wm()
    dx = end_x - start_x
    dz = end_z - start_z
    if abs(dx-x)> self.x2.get_par('retry_deadband'):
        print "WARNING: x2 did not reach desired position of %f! Check motors! now at: %f, deadband %f "%(start_x+x,end_x,self.x2.get_par('retry_deadband'))
    if abs(dz-z) > self.z2.get_par('retry_deadband'):
        print "WARNING: z2 did not reach desired position of %f! Check motors! now at: %f, deadband %f "%(start_z+z,end_z,self.z2.get_par('retry_deadband'))

  def tweakParallel(self,p,ID=None):
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    if ID=='Si':
      th = self.th2Si.wm()
      self.x2.move_relative(p*sin(th*pi/180))
      self.z2.move_relative(p*cos(th*pi/180))
    elif ID=='C':
      th = self.th2C.wm()
      self.x2.move_relative(p*sin(th*pi/180))
      self.z2.move_relative(p*cos(th*pi/180))
    else:
      raise ValueError('Invalid material ID: %s'%ID)

  def setE1(self,E,ID=None, reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    (th,z) = self.getLomGeom(E,ID,reflection)
    if ID=='Si':
      self.th1Si.set(th)
      self.z1Si.set(-z)
    elif ID=='C':
      self.th1C.set(th)
      self.z1C.set(-z)
    else:
      raise ValueError('Invalid material ID: %s'%ID)

  def setE(self, E, ID=None, reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    (th,z) = self.getLomGeom(E, ID, reflection)
    if ID=='Si':
      self.th1Si.set(th)
      self.th2Si.set(th)
      self.z1Si.set(-z)
      self.z2Si.set(z)
    elif ID=='C':
      self.th1C.set(th)
      self.th2C.set(th)
      self.z1C.set(-z)
      self.z2C.set(z)
    else:
      raise ValueError('Invalid material ID: %s'%ID)
  
  ## LOM E1 ##
  def moveE1C(self,E,ID='C',reflection=(1,1,1)):
    self.moveE1(E, ID, reflection)

  def getE1C(self, ID='C', reflection=(1,1,1)):
    return self.getE1(ID, reflection)

  def waitE1C(self):
    self.waitE1()

  ## LOM E2  ##
  def moveE2C(self,E,ID='C',reflection=(1,1,1)):
    self.moveE2(E, ID, reflection)

  def getE2C(self,ID='C', reflection=(1,1,1)):
    return self.getE2(ID, reflection)

  def waitE2C(self):
    self.waitE2()

  ## LOM E
  def moveEC(self,E,ID='C', reflection=(1,1,1)):
    self.moveE(E,ID,reflection)
  
  def moveECtweak(self,E,ID='C', reflection=(1,1,1)):
    self.moveEtweak(E,ID,reflection)
  
  def getEC(self, ID='C', reflection=(1,1,1)):
    return self.getE(ID, reflection)

  def waitEC(self):
    self.waitE()

  def tweakXC(self,x):
    self.tweakX(x,ID='C')

  def tweakParallelC(self,p):
    self.tweakParallel(p,ID='C')

  def setE1C(self,E,ID='C', reflection=(1,1,1)):
    self.setE1(E,ID,reflection)

  def setEC(self, E, ID='C', reflection=(1,1,1)):
    self.setE(E,ID,reflection)

  # Silicon macros ##############################
  ## LOM E1 ##
  def moveE1Si(self,E,ID='Si',reflection=(1,1,1)):
    self.moveE1(E, ID, reflection)

  def getE1Si(self, ID='Si', reflection=(1,1,1)):
    return self.getE1(ID, reflection)

  def waitE1Si(self):
    self.waitE1()

  ## LOM E2  ##
  def moveE2Si(self,E,ID='Si',reflection=(1,1,1)):
    self.moveE2(E, ID, reflection)

  def getE2Si(self,ID='Si', reflection=(1,1,1)):
    return self.getE2(ID, reflection)

  def waitE2Si(self):
    self.waitE2()

  ## LOM E
  def moveESi(self,E,ID='Si', reflection=(1,1,1)):
    self.moveE(E,ID,reflection)
  
  def moveESitweak(self,E,ID='Si', reflection=(1,1,1)):
    self.moveEtweak(E,ID,reflection)
  
  def getESi(self, ID='Si', reflection=(1,1,1)):
    return self.getE(ID, reflection)

  def waitESi(self):
    self.waitE()

  def tweakXSi(self,x):
    self.tweakX(x,ID='Si')

  def tweakParallelSi(self,p):
    self.tweakParallel(p,ID='Si')

  def setE1Si(self,E,ID='Si', reflection=(1,1,1)):
    self.setE1(E,ID,reflection)

  def setESi(self, E, ID='Si', reflection=(1,1,1)):
    self.setE(E,ID,reflection)

  # Silicon 333 macros ##############################
  ## LOM E1 ##
  def moveE1Si333(self,E,ID='Si',reflection=(3,3,3)):
    self.moveE1(E, ID, reflection)

  def getE1Si333(self, ID='Si', reflection=(3,3,3)):
    return self.getE1(ID, reflection)

  def waitE1Si333(self):
    self.waitE1()

  ## LOM E2  ##
  def moveE2Si333(self,E,ID='Si',reflection=(3,3,3)):
    self.moveE2(E, ID, reflection)

  def getE2Si333(self,ID='Si', reflection=(3,3,3)):
    return self.getE2(ID, reflection)

  def waitE2Si333(self):
    self.waitE2()

  ## LOM E
  def moveESi333(self,E,ID='Si', reflection=(3,3,3)):
    self.moveE(E,ID,reflection)
  
  def moveESi333tweak(self,E,ID='Si', reflection=(3,3,3)):
    self.moveEtweak(E,ID,reflection)
  
  def getESi333(self, ID='Si', reflection=(3,3,3)):
    return self.getE(ID, reflection)

  def waitESi333(self):
    self.waitE()

  def tweakXSi333(self,x):
    self.tweakX(x,ID='Si')

  def tweakParallelSi333(self,p):
    self.tweakParallel(p,ID='Si')

  def setE1Si333(self,E,ID='Si', reflection=(3,3,3)):
    self.setE1(E,ID,reflection)

  def setESi333(self, E, ID='Si', reflection=(3,3,3)):
    self.setE(E,ID,reflection)

  # Simulation macros ##############################
  def simulate(self,E,ID=None,reflection=None):
    if reflection is None:
      # try to determine possible current reflection
      reflection=self.get_reflection(astuple=True, check=True)
    if ID is None:
      # try to determine possible current material ID
      ID=self.get_material(check=True)
    (th,z) = self.getLomGeom(E,ID,reflection)
    print "Motor positions to achieve requested configuration:"
    print "\tth1%s:\t%+9.3f" % (ID, th)
    print "\tth2%s:\t%+9.3f" % (ID, -th)
    print "\tdr:\t%+9.3f" % (2*th)
    print "\tz1%s:\t%+9.3f" % (ID, -z)
    print "\tz2%s:\t%+9.3f" % (ID, z)

  # Detailed status displays #######################
  def detailed_status_tower1(self, toPrint=True):
    str = "** Tower 1 (Crystals) Detailed Status **\n"
    keys = self.tower1motors.keys()
    keys.sort()
    formatTitle = "%15s %20s  %18s  %4s  %10s  %10s  %10s  %10s  %10s  %10s  %7s  %7s  %7s  %7s  %5s  %5s  %7s  %20s  %20s  %20s  %20s\n"
    formatEntry = "%15s %20s  %18s  %4s  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %7.1f  %7.1f  %7.1f  %7.1f  %5.1f  %5.1f  %7.1f  %20.12E  %20.12E  %20.12E  %20.12E\n"
    str += formatTitle % ("XCS Name", "EPICS Name", "PV Name", "EGU", "User", "User LL", "User HL", "Dial", "Dial LL", "Dial HL", "Vmin", "Vmin", "Vmax", "Vmax", "Accel", "Decel", "% Run", "USER OFS", "SREV", "UREV", "MRES")
    str += formatTitle % ("", "", "", "", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(Rev/s)", "(EGU/s)", "(Rev/s)", "(EGU/s)", "(s)", "(s)", "Current", "(EGU)", "(Step/Rev)", "(EGU/Rev)", "(Egu/Step)")
    for key in keys:
      m = self.tower1motors[key]
      run_current = 0.
      try:
        run_current = float(m.get_par("run_current",":"))
      except Exception, e:
        pass
      str += formatEntry % (self.objName+"."+key,m.get_par("description"), m.pvname, m.get_par("units"), m.wm(), m.get_par("low_limit"), m.get_par("high_limit"), m.wm_dial(), m.get_par("dial_low_limit"), m.get_par("dial_high_limit"), m.get_par("s_base_speed"), m.get_par("base_speed"), m.get_par("s_speed"), m.get_par("slew_speed"), m.get_par("acceleration"), m.get_par("back_accel"), run_current, m.get_par("offset"),  m.get_par("s_revolutions"), m.get_par("u_revolutions"), m.get_par("resolution"))
    if (toPrint):
      print str
    else:
      return str

  def detailed_status_tower2(self, toPrint=True):
    str = "** Tower 2 (Crystals) Detailed Status **\n"
    keys = self.tower2motors.keys()
    keys.sort()
    formatTitle = "%15s %20s  %18s  %4s  %10s  %10s  %10s  %10s  %10s  %10s  %7s  %7s  %7s  %7s  %5s  %5s  %7s  %20s  %20s  %20s  %20s\n"
    formatEntry = "%15s %20s  %18s  %4s  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %7.1f  %7.1f  %7.1f  %7.1f  %5.1f  %5.1f  %7.1f  %20.12E  %20.12E  %20.12E  %20.12E\n"
    str += formatTitle % ("XCS Name", "EPICS Name", "PV Name", "EGU", "User", "User LL", "User HL", "Dial", "Dial LL", "Dial HL", "Vmin", "Vmin", "Vmax", "Vmax", "Accel", "Decel", "% Run", "USER OFS", "SREV", "UREV", "MRES")
    str += formatTitle % ("", "", "", "", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(Rev/s)", "(EGU/s)", "(Rev/s)", "(EGU/s)", "(s)", "(s)", "Current", "(EGU)", "(Step/Rev)", "(EGU/Rev)", "(Egu/Step)")
    for key in keys:
      m = self.tower2motors[key]
      run_current = 0.
      try:
        run_current = float(m.get_par("run_current",":"))
      except Exception, e:
        pass
      str += formatEntry % (self.objName+"."+key,m.get_par("description"), m.pvname, m.get_par("units"), m.wm(), m.get_par("low_limit"), m.get_par("high_limit"), m.wm_dial(), m.get_par("dial_low_limit"), m.get_par("dial_high_limit"), m.get_par("s_base_speed"), m.get_par("base_speed"), m.get_par("s_speed"), m.get_par("slew_speed"), m.get_par("acceleration"), m.get_par("back_accel"), run_current, m.get_par("offset"),  m.get_par("s_revolutions"), m.get_par("u_revolutions"), m.get_par("resolution"))
    if (toPrint):
      print str
    else:
      return str

  def detailed_status_tower3(self, toPrint=True):
    str = "** Tower 3 (Diagnostics) Detailed Status **\n"
    keys = self.tower3motors.keys()
    keys.sort()
    formatTitle = "%15s %20s  %18s  %4s  %10s  %10s  %10s  %10s  %10s  %10s  %7s  %7s  %7s  %7s  %5s  %5s  %7s  %20s  %20s  %20s  %20s\n"
    formatEntry = "%15s %20s  %18s  %4s  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %7.1f  %7.1f  %7.1f  %7.1f  %5.1f  %5.1f  %7.1f  %20.12E  %20.12E  %20.12E  %20.12E\n"
    str += formatTitle % ("XCS Name", "EPICS Name", "PV Name", "EGU", "User", "User LL", "User HL", "Dial", "Dial LL", "Dial HL", "Vmin", "Vmin", "Vmax", "Vmax", "Accel", "Decel", "% Run", "USER OFS", "SREV", "UREV", "MRES")
    str += formatTitle % ("", "", "", "", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(Rev/s)", "(EGU/s)", "(Rev/s)", "(EGU/s)", "(s)", "(s)", "Current", "(EGU)", "(Step/Rev)", "(EGU/Rev)", "(Egu/Step)")
    for key in keys:
      m = self.tower3motors[key]
      run_current = 0.
      try:
        run_current = float(m.get_par("run_current",":"))
      except Exception, e:
        pass
      str += formatEntry % (self.objName+"."+key,m.get_par("description"), m.pvname, m.get_par("units"), m.wm(), m.get_par("low_limit"), m.get_par("high_limit"), m.wm_dial(), m.get_par("dial_low_limit"), m.get_par("dial_high_limit"), m.get_par("s_base_speed"), m.get_par("base_speed"), m.get_par("s_speed"), m.get_par("slew_speed"), m.get_par("acceleration"), m.get_par("back_accel"), run_current, m.get_par("offset"),  m.get_par("s_revolutions"), m.get_par("u_revolutions"), m.get_par("resolution"))
    if (toPrint):
      print str
    else:
      return str

  def detailed_status(self, toPrint=True):
    str = "** LODCM Detailed Status **\n"
    str += self.detailed_status_tower1(False) + self.detailed_status_tower2(False) + self.detailed_status_tower3(False)
    if (toPrint):
      print str
    else:
      return str
