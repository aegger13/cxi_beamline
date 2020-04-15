from blutil import printnow, dec2bin, estr
from periodictable import xsf
from periodictable import formula as ptable_formula
import numpy as np
import sys
from pypslog import logprint
from time import sleep


def getAttLen(E,material="Si",density=None):
  """ get the attenuation length (in meter) of material (default Si), if no
      parameter is given for the predefined energy;
      then T=exp(-thickness/att_len); E in keV"""
  att_len = float(attenuation_length(material,density=density,energy=E))
  return att_len

# This function was part of our Frankenstein periodic table build.
# It now lives here because it was never an official part of the module.
# I copied it in and adjusted namespaces accordingly.
def attenuation_length(compound, density=None, natural_density=None,
								energy=None, wavelength=None):
    """
    Calculates the attenuation length for a compound
		Transmisison if then exp(-thickness/attenuation_length)

    :Parameters:
        *compound* : Formula initializer
            Chemical formula.
        *density* : float | |g/cm^3|
            Mass density of the compound, or None for default.
        *natural_density* : float | |g/cm^3|
            Mass density of the compound at naturally occurring isotope abundance.
        *wavelength* : float or vector | |Ang|
            Wavelength of the X-ray.
        *energy* : float or vector | keV
            Energy of the X-ray, if *wavelength* is not specified.

    :Returns:
        *attenuation_length* : vector | |m|
            as function of (energy)

    :Notes:

    against http://henke.lbl.gov/optical_constants/
    """
    if energy is not None: wavelength = xsf.xray_wavelength(energy)
    assert wavelength is not None, "scattering calculation needs energy or wavelength"
    if (np.isscalar(wavelength)): wavelength=np.array( [wavelength] )
    n = xsf.index_of_refraction(compound=compound,
                             density=density, natural_density=natural_density,
                             wavelength=wavelength)
    attenuation_length = (wavelength*1e-10)/ (4*np.pi*np.imag(n))
    return np.abs(attenuation_length)



def calcTrasmissionForList(att_list,E):
  T=1
  for a in att_list: T*=a.transmission(E)
  return T

def calcTrasmissionForThick(d,E,material="Si",density=None):
  """ returns transmission for a given thickness (in meter);
      E is in keV
      material can also be a compund (like SiO2)
      density: in gr/cm^3; if abset default is used; no defaults for compounds
  """
  att_len = getAttLen(E,material,density)
  return np.exp(-d/att_len)

def findFiltersForTrasm(att_list,transmission,E):
  """ Determines which filters have to be moved in the beam to
      achieve a transmission as close as possible to the requested one.
  Note : the function does not move the filters
       to use for calculation"""
  tobe_in  = []
  tobe_out = []
  n = len(att_list)
  deltaT_min = 1e35
  for i in range(1<<n):
    conf = dec2bin(i)
    d = 0
    T=1
    for s in range(len(conf)):
      if (conf[-(s+1)] == "1"):
        T *= att_list[s].transmission(E)
    deltaT = abs(T-transmission)
#    print d_needed,conf,d,dist,dist_min
    if (deltaT < deltaT_min):
      deltaT_min=deltaT
#      print d_needed,d,conf,dist_min
      conf_min = conf
  for s in range(len(conf_min)):
    if (conf_min[-(s+1)] == "1"):
      tobe_in.append(att_list[s])
    else:
      tobe_out.append(att_list[s])
  for s in range(len(conf_min),n):
    tobe_out.append(att_list[s])
  return (tobe_in,tobe_out)


def moveIN(att_list,fast=0):
  """ move filters define by the tuple tobe_in in the beam """
  for f in att_list: f.movein()
  if (not fast):
#    sleep(0.3)
    wait(att_list)

def moveOUT(att_list,fast=0):
  """ move filters define by the tuple tobe_in out the beam, the others out """
  for f in att_list: f.moveout()
  if (not fast):
#    sleep(0.3)
    wait(att_list)

def wait(att_list): 
  for f in att_list: f.wait()

def check_filters_position(att_list):
  """ Check which filters are `in` and return a list """
  n = len(att_list)
  list_in = []
  list_out = []
  list_unknown = []
  for i in range(n):
    if att_list[i].isin():
      list_in.append(i)
    elif att_list[i].isout():
      list_out.append(i)
    else:
      list_unknown.append(i)
  return (list_in,list_out,list_unknown)


def getT(att_list,E,printit=1):
  """ Check which filters are `in` and calculate the transmission
      for the energy defined with the `setE` command
      The finding is returned as dictionary """
  wait(att_list)
  n=len(att_list)
  (fin,fout,funknown)=check_filters_position(att_list)
  att_list_in=[]
  s_title = "filter# |"
  for i in range(n):
    s_title += "%d|" % i
  s_in    = " IN     |"
  s_out   = " OUT    |"
  ret = dict()
  for i in range(n):
    if i in fin:
      att_list_in.append(att_list[i])
      s_in +=estr("X",color="yellow",type="normal")+"|"
      s_out+=" |"
    elif (i in fout):
      s_in +=" |"
      s_out+=estr("X",color="green",type="normal")+"|"
    else:
      s_in +=estr("?",color="red",type="normal")+"|"
      s_out+=estr("?",color="red",type="normal")+"|"
  T = calcTrasmissionForList(att_list_in,E)
  if (E<12.500):
    T3rd = calcTrasmissionForList(att_list_in,E*3)
    ret['1st_Si'] = T
    ret['3rd_Si'] = T3rd
    s  = "Transmission for 1st harmonic (E= %.2fkeV): %.3e\n" % (E,T)
    s += "Transmission for 3rd harmonic (E=%.2fkeV): %.3e\n" % (E*3,T3rd)
  else:
    T1st = calcTrasmissionForList(att_list_in,E/3)
    ret['1st_Si'] = T1st
    ret['3rd_Si'] = T
    s  = "Transmission for 1st harmonic (E= %.2fkeV): %.3e\n" % (E/3,T1st)
    s += "Transmission for 3rd harmonic (E=%.2fkeV): %.3e\n" % (E,T)
  ret["E"]=T
  sret = s_title + "\n" + s_out + "\n" + s_in + "\n" + s
  if (printit):
    print sret
  return (ret,sret)

def getTvalue(att_list,E):
  """ returns float with current transmission. (for the energy previously set)
  """
  (ret,todel) = getT(att_list,E,printit=0)
  return ret["E"]

def setTfast(att_list,transmission,E,printit=1,domove=1):
  """ as setT but it dows not wait for motors ... (and IN and OUT commands
      are sent at the sae time"""
  setT(att_list,transmission,E,fast=True,printit=printit,domove=domove)

def setT(att_list,transmission,E,fast=False,printit=1,domove=1):
  """ Determines which filters have to be moved in othe beam to
      achieve a transmission as close as possible to the requested one.
Note : the function moves the filters
Note2: use the `setE` command before to choose which energy 
       to use for calculation"""
  (tobe_in,tobe_out) = findFiltersForTrasm(att_list,transmission,E)
  if (domove):
    if (printit): printnow("Moving attenuators IN")
    moveIN(tobe_in,fast=fast)
    if (printit): printnow("... done\n")
    if (printit): printnow("Moving attenuators OUT")
    moveOUT(tobe_out,fast=fast)
    if (printit): printnow("... done\n")
  T =calcTrasmissionForList(tobe_in,E)
  T3=calcTrasmissionForList(tobe_in,E*3)
  if (printit and (not fast)):
    sleep(0.5)
    getT(att_list,E)
  return T,T3
