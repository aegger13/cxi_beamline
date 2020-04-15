import socket
import time
import struct

class value(object):
  def __init__(self,v,u,isint=False):
    if (isint):
      self.v=int(v)
    else:
      self.v=float(v)
    self.u=u
  def __repr__(self):
    return "value,units = %e,%s" % (self.v,self.u)

class Wavesurfer:

  def __init__(self,hostname):
    self.address = (hostname, 1861)
    self.socket = socket.socket()
    self.socket.connect(self.address)
    
  def query(self,command):
    self.socket.send(self.__makeCommand(command))
    reply = self.socket.recv(4096)
    return reply[8:-1]
  
  def send(self,command):
    self.socket.send(self.__makeCommand(command))
  
  def __makeCommand(self,command):
    header = [0x81,1,0,0]
    n = len (command)
    count = [0, 0, (n>>8) & 0xff, n & 0xff]

    header = struct.pack('BBBBBBBB', 0x81,1,0,0, 0, 0, (n>>8) & 0xff, n & 0xff)
    return header+command  
    
  def close(self):
    self.socket.close()

  def display_on(self):
    self.send("DISP ON")

  def display_off(self):
    self.send("DISP OFF")

  def acquire_for_time(self,t):
    self.send("TRMD NORM")
#    self.send("TRMD AUTO")
    self.clear_sweeps()
    time.sleep(t)
    self.send("TRMD STOP")
    return

# A bit higher level commands start here    
  def clear_sweeps(self):
    self.send("CLEAR_SWEEPS")
    
  def wait_for_pulse(self):
    while self.query('TRMD?') == 'SINGLE':
      pass

  def __get_custom_par(self,what):
    cmd = "PARAMETER_STATISTICS? CUST,%s" % what
    reply = self.query(cmd)
    # reply syntax PAST CUST,what,v1 units,v2 units, ...
    a=reply.split(",");
    values=[]
    units =[]
    for i in range(4):
      tmp = a[i+2];
      if tmp=='UNDEF':
        continue
      (v,u)=tmp.split()
      values.append(v);
      units.append(u);
    return values,units

  def get_all_pars_for_measurement(self,which):
    cmd = "PARAMETER_STATISTICS? CUST, P%s" % which
    reply = self.query(cmd)
    # reply syntax PAST CUST,what,v1 units,v2 units, ...
    a=reply.split(",");
    r={}
    r["P%s" % which] = a[2]
    r["channel"]   = a[3]
    for i in range(4,14,2):
      name = a[i]
      v    = a[i+1].split()
      r[name]=value(v[0],v[1])
    r["SWEEPS"]=int(float(a[-1]))
    return r

  def get_averages(self):
    return self.__get_custom_par("AVG")

  def get_sigma(self):
    return self.__get_custom_par("SIGMA")

  def get_values(self):
    reply=self.query('PAVA? CUST1, CUST2, CUST3, CUST4');
#   reply syntax: 1,val1,OK,2,val2,OK,...
    a=reply.split(",");
    values=[]
    for i in range(4):
      values.append(a[3*i+1]);
    return values

  def get_new_values(self):
    self.clear_sweeps()
    self.wait_for_pulse()
    return self.get_values()
    

