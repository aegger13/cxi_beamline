""" Utilities to handle strings, guess which beamline are you running from,
    time/date, etc"""

import sys
import time
import datetime
import re
import os
import struct
import socket
import subprocess
import signal
import contextlib
import numpy as np

def parse_cnf_file(beamline,field="configdb_path"):
  beamline=beamline.strip()
  fname = "/reg/g/pcds/dist/pds/%s/scripts/%s.cnf" % (beamline,beamline)
  f=open(fname,"r")
  lines = f.readlines()
  match = None
  flen = len(field)
  for l in lines:
    ls = l.strip()
    ls = ls.replace(" ","")
    ls = ls.replace("\t","")
    # == 0 means that is not commented out
    if (ls[0:flen] == field):
      match = ls.replace('"',"")
      match = match.replace("'","")
  if (match is not None):
    return match.split("=")[1]
  else:
    return None

def guessBeamline():
  """ Guess beamline from hostname xpp-daq -> xpp"""
  host = socket.gethostname(); # returns for example xpp-daq
  return host.split("-")[0];   # returns xpp

def guessRunNumber():
    import psdm.experiment_info
    beamline = guessBeamline()
    experiment = psdm.experiment_info.active_experiment(beamline.upper())
    expID = experiment[2]
    files = psdm.experiment_info.get_open_files(expID)
    return int(files[0]["run"])

def guessAmiProxy(hutch=None,cnf=None):
  """ Guess the host of the ami_proxy process from procmgr """
  if cnf is None:
    if hutch is None:
      hutch = guessBeamline()
    cnf = '/reg/g/pcds/dist/pds/{hutch}/scripts/{hutch}.cnf'.format(hutch=hutch)
  domain_re = re.compile('.pcdsn$')
  ip_re = re.compile('^(?:[\d\.]{7,15}|[\w-]+)\s+ami_proxy\s+.*?\s+-I\s+(?P<ip>\d+\.\d+\.\d+\.\d+)\s+')
  args=['/reg/g/pcds/dist/pds/tools/procmgr/procmgr', 'status', cnf, 'ami_proxy']
  with timeout_context(1, msg="procmgr timed out!"):
    try:
      output = subprocess.check_output(args)
    except subprocess.CalledProcessError as err:
      output = err.output
    for line in output.split("\n"):
      ip_match = ip_re.match(line)
      if ip_match:
        host, _, _ = socket.gethostbyaddr(ip_match.group('ip'))
        return domain_re.sub('', host)

def guessAmiGroup(hutch=None,cnf=None):
  """ Guess the ami multicast group of the daq from procmgr """
  if cnf is None:
    if hutch is None:
      hutch = guessBeamline()
    cnf = '/reg/g/pcds/dist/pds/{hutch}/scripts/{hutch}.cnf'.format(hutch=hutch)
  search_list = ['amicoll0', 'ami_client1', 'ami_client']
  domain_re = re.compile('.pcdsn$')
  for procid in search_list:
    ip_re = re.compile('^(?:[\d\.]{7,15}|[\w-]+)\s+%s+\s+.*?\s+-s\s+(?P<ip>\d+\.\d+\.\d+\.)\d+'%procid)
    args = ['/reg/g/pcds/dist/pds/tools/procmgr/procmgr', 'status', cnf, procid]
    with timeout_context(1, msg="procmgr timed out"):
      try:
        output = subprocess.check_output(args)
      except subprocess.CalledProcessError as err:
        output = err.output
      for line in output.split("\n"):
        ip_match = ip_re.match(line)
        if ip_match:
          return struct.unpack("!L", socket.inet_aton(ip_match.group('ip')+'0'))[0]

def cartesian_to_spherical(x,y,z):
    az = np.rad2deg( np.arctan2(x,z) )
    el = np.rad2deg( np.arctan2(y,np.sqrt(z**2+x**2)) )
    ra = np.sqrt ( x**2 + y**2 + z**2 )
    return (ra,az,el)

def now():
  """ returns string with current date and time (with millisecond resolution)"""
  now = datetime.datetime.now()
  return "%04d-%02d-%02d %02d:%02d:%02d.%03d" % ( now.year, now.month,now.day,
                     now.hour,now.minute,now.second,int(now.microsecond/1e3))

def today():
  """ returns string with current date"""
  now = datetime.datetime.now()
  return "%04d-%02d-%02d" % ( now.year, now.month,now.day)

def estr(string,color="red",type="bold"):
  """ returns an enhanced string, current colors defined: red|green,
                                  current type defined: bold"""
  str = ""
  if ( color == "gray" ):
    str += "\x1b[30m"
  elif ( color == "red" ):
    str += "\x1b[31m"
  elif ( color == "green" ):
    str += "\x1b[32m"
  elif ( color == "orange" or color == "yellow" ):
    str += "\x1b[33m"
  elif ( color == "blue" ):
    str += "\x1b[34m"
  elif ( color == "magenta" ):
    str += "\x1b[35m"
  elif ( color == "cyan" ):
    str += "\x1b[36m"
  elif ( color == "white" ):
    str += "\x1b[37m"
  elif ( color == "crimson" ):
    str += "\x1b[38m"
  elif ( color == "hred" ):
    str += "\x1b[41m"
  elif ( color == "hgreen" ):
    str += "\x1b[42m"
  elif ( color == "hbrown" ):
    str += "\x1b[43m"
  elif ( color == "hblue" ):
    str += "\x1b[44m"
  elif ( color == "hmagenta" ):
    str += "\x1b[45m"
  elif ( color == "hcyan" ):
    str += "\x1b[46m"
  elif ( color == "hgray" ):
    str += "\x1b[47m"
  elif ( color == "hcrimson" ):
    str += "\x1b[48m"
  elif ( color == "mec" ):
    str += "\x1b[38;5;214m"
  elif ( color == "xcs" ):
    str += "\x1b[38;5;93m"
  elif ( color == "xpp" ):
    str += "\x1b[38;5;40m"
  elif ( color == "mfx" ):
    str += "\x1b[38;5;202m"
  elif ( color == "amo" ):
    str += "\x1b[38;5;27m"
  elif ( color == "sxr" ):
    str += "\x1b[38;5;250m"
  elif ( color == "cxi" ):
    str += "\x1b[38;5;196m"
  elif (color==None):
    str = str
  if (type == "bold"):
    str += "\x1b[1m"
  str += string
  str += "\x1b[0m"; # reset color
  return str

def st2bw(stat):
  """takes a string, and stips it of the color and type commands defined in estr"""
  p = re.compile('\\x1b\[\d+(;\d+;\d+)?m')
  return p.sub('', stat)

def dec2bin(n):
    """converts denary integer n to binary string (used for lusiatt)"""
    bStr = ''
    if n < 0:  raise ValueError, "must be a positive integer"
    if n == 0: return '0'
    while n > 0:
        bStr = str(n % 2) + bStr
        n = n >> 1
    return bStr

def time_to_text(t):
  """converts floating number as string like 3s 004ms 024us 134ns 003ps 104fs"""
  t="%0.15f" % t
  idx = t.index(".")
  s  = int( t[0      : idx    ])
  ms = int( t[idx+1  : idx+4  ])
  us = int( t[idx+4  : idx+7  ])
  ns = int( t[idx+7  : idx+10 ])
  ps = int( t[idx+10 : idx+13 ])
  fs = int( t[idx+13 : idx+16 ])
  text = "%ss %03dms %03dus %03dns %03dps %03dfs" % (s,ms,us,ns,ps,fs)
  return text

def printnow(s):
  print s,
  sys.stdout.flush()

def terminal_size():
  """returns a tuple with (nrows,ncols) of current terminal"""
  import termios, fcntl, struct, sys
  s = struct.pack("HHHH", 0, 0, 0, 0)
  fd_stdout = sys.stdout.fileno()
  x = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, s)
  (rows,cols,xpixel,ypixel)=  struct.unpack("HHHH", x)
  return (rows,cols)

def notice(string):
  """prints a string starting from the beginning of the line and spanning the
  entire terminal columns, useful for updating values ...
  notice("this is the first value 1.2"); sleep(1); notice("this is the second one 1.4 that will mask the first...")
  """
  (nrows,ncols)=terminal_size()
  format = "\r%%-%ds" % ncols
  sys.stdout.write( format % string)
  sys.stdout.flush()

def write_array_to_file(a,fname):
  f=file(fname,"w")
  for l in a:
    f.write("%s\n" % l)
  f.close()

def array_string_to_float(a):
  c=[]
  for e in a:
    c.append(float(e))
  return c



def eventcode_to_time(eventcode):
  eventcode=int(eventcode)
  e = {}
  e[9]  = 12900 
  e[10] = 12951 
  e[11] = 12961 
  e[12] = 12971 
  e[13] = 12981 
  e[14] = 12991 
  e[15] = 13001 
  e[16] = 13011 
  e[40] = 12954 
  e[41] = 12964 
  e[42] = 12974 
  e[43] = 12984 
  e[44] = 12994 
  e[45] = 13004 
  e[46] = 13014 
  e[140]= 11850 
  e[150]= 11859
  e[162]= 11840
  if (eventcode in e):
    ticks = e[eventcode]
  elif (eventcode >= 67 and eventcode<= 98):
    ticks = e[140]+eventcode
  elif (eventcode>140 and eventcode<=159):
    ticks = e[140]+(eventcode-140)
  elif (eventcode>=162 and eventcode<=198):
    ticks = e[140]+eventcode
  else:
    ticks = 0
  return ticks/119e6


def eventcode_time_from140(eventcode):
  return eventcode_to_time(eventcode)-eventcode_to_time(140)

#def write_to_file(filename,var):
  #"""Writes single variable (no matter what structure) to file \"filename\". Only the data is written, not the variable name. Load again with read_from_file of same module."""
  #f=open(filename,'w')
  #f.write(simplejson.dumps(var,sort_keys=True,indent=3))
  #f.close()
  
def read_from_file(filename):
  """Writes single variable (no matter what structure) to file \"filename\". Only the data is written, not the variable name. Load again with read_from_file of same module."""
  try:	  
    f = open(filename)
    var = eval(f.read())
    f.close()
    return var

  except:
    print "File not found (%s)." %filename   
    return []

def iterfy(iterable):
  if isinstance(iterable, basestring):
      iterable = [iterable]
  try:
      iter(iterable)
  except TypeError:
      iterable = [iterable]
  return iterable


def linlogspace(start,middle,end,linear_spacing,log_npoints):
  delaylist = []
  if type(linear_spacing) is int:
    delaylist.extend(list(np.linspace(start,middle,linear_spacing+1))[:-1])
  else:
    delaylist.extend(list(np.arange(start,middle,linear_spacing)))
  
  delaylist.extend(list(np.logspace(np.log10(middle),np.log10(end),log_npoints)))
  return delaylist

def irange(start,end,step):
  if (end-start)/step <0:
    return np.array([])
  else:
    tv = start
    spac = np.spacing(start)+np.spacing(end)
    out = []
    if step>0:
      while tv <= end+spac:
	out.append(tv)
	tv+=step
	spac += np.spacing(step)
    elif step<0:
      while tv >= end+spac:
	out.append(tv)
	tv+=step
	spac += np.spacing(step)
    else:
      out=[start]
    return np.asarray(out)

def ilogspace(start,end,Npoints):
  return np.logspace(np.log10(start),np.log10(end),Npoints)





def currentRunNum():
  p1 = ["/reg/g/pcds/pds/grabber/lib/python2.7/site-packages","/reg/g/pcds/controls/pyps/"]
  for p in p1:
    if p not in sys.path:
      sys.path.append(p)
  import psdm.experiment_info
  beamline = guessBeamline()
  experiment = psdm.experiment_info.active_experiment(beamline.upper())
  expID = experiment[2]
  files = psdm.experiment_info.get_open_files(expID)
  return int(files[0]["run"])


def list_to_string(list,sep=" "):
  return sep.join(list)


def delays_to_string(list,sep=" "):
  return sep.join([num2sci(t,unit="s") for t in list])

def num2sci_old(n,unit="s"):
  if (np.abs(n*1e3)>1):
    s = "%.2fm" % (n*1e3)
  if (np.abs(n*1e6)>1):
    s = "%.2fu" % (n*1e6)
  elif (np.abs(n*1e9)>1):
    s = "%.2fn" % (n*1e9)
  else:
    s ="%.2fp" % (n*1e12)
  return s+unit

def num2sci(num,unit='',precision=3):
  isneg = False
  iszero=False
  if num<0:
    num=-1*num
    isneg = True
  elif num==0:
    iszero=True
  if not iszero:
    exponents = np.arange(-24,24+1,3)
    prefixes =['y','z','a','f','p','n','u','m','','k','M','G','T','P','E','Z','Y']
    exponNum = np.floor(np.log10(num))
    exponSci = np.floor(exponNum/3)*3
    if not exponSci in exponents:
      exponSci = exponents[np.argmin(exponents-exponSci)]
    sci = num / 10**exponSci
    prefix = prefixes[list(exponents).index(exponSci)]
    sci = round(sci,precision)
  if isneg:
    sci=-1*sci
  elif iszero:
    sci = 0
    exponSci=0
    prefix = ''
  if unit is '':
    return sci,exponSci
  else:
    return str(sci)+prefix+unit

class TimeoutException(Exception):
    pass

def make_raise_timeout(msg=""):
    def raise_timeout(signum, frame):
        raise TimeoutException(msg)
    return raise_timeout

@contextlib.contextmanager
def timeout_context(tmo, msg=""):
    old_handler = signal.signal(signal.SIGALRM, make_raise_timeout(msg))
    signal.setitimer(signal.ITIMER_REAL, tmo)
    try:
        yield
    except TimeoutException as exc:
        print exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
