import urllib
import urllib2
import simplejson as json
import os
import sys
import dateutil, datetime
import time as timemodule
import numpy as np
import matplotlib.dates as mdates
import pylab as p
import tools
from pycasi import casiTools, casi
from blutil import printnow

old_archive_path = "/reg/d/pscaa"
new_archive_url = "http://pscaa02:17668/retrieval"
urlbase = new_archive_url + "/data/getData.json?pv={0}"
urlfrom = "&from={0}"
urlto = "&to={0}"
nochunk = "&donotchunk"
date_spec_format = "{0:04}-{1:02}-{2:02}T{3:02}:{4:02}:{5:02}.{6:03}Z"
bplurl = "http://pscaa02.slac.stanford.edu:17665/mgmt/bpl/" # Will be useful for searching through PVs

class epicsarchive:
  def __init__(self, hutch=None, start_year=None, end_year=None):
    self.considerOldArch = bool(hutch)
    if self.considerOldArch:
      self.hutch = hutch.upper()
      self.archive_base_path = old_archive_path
      self.end_year = end_year or datetime.datetime.now().year
      self.start_year = start_year or self.end_year - 2
      self.index_file_list = []
      for year in range(self.start_year, self.end_year+1):
          self.index_file_list.append(os.path.join(self.archive_base_path, self.hutch, str(year), 'master_index'))
      self.index_file_list.append(os.path.join(self.archive_base_path, self.hutch, 'current_index'))
      self.arch = []
      for archfile in self.index_file_list:
        tarch = casi.archive()
        tarch.open(archfile)
        self.arch.append(tarch)

  def get_points(self, pv, time_selection=30, chunk=False):
    t, x = self.pv_archive_data(pv, time_selection, chunk)
    pts = []
    for time, pos in zip(t, x):
        pts.append((time, pos))
    return pts

  def plot_data(self, pv, time_selection=30, chunk=False):
    t, x = self.pv_archive_data(pv, time_selection, chunk)
    tools.nfigure("Epics archive " + pv)
    p.plot(t,x,"k.-")
    p.ylabel(pv)
    p.show()

  def print_data(self, pv, time_selection=30, chunk=False):
    time, data = self.pv_archive_data(pv, time_selection, chunk)
    for t,d in zip(time, data):
      printnow("%s\t%f\n"%(t, d))

  def pv_archive_data(self, pv, time_selection=30, chunk=False):
    try:
      t1, x1 = self.new_archive_data(pv, time_selection, chunk)
    except StandardError as e:
      print "Could not connect to new archiver. {0}".format(e)
      print "This machine probably does not have access to pscaa02."
      t1, x1 = ([], [])
#    if len(t1) > 0:
#      print "Got {0} points from new archiver from {1} to {2}.".format(len(t1), t1[0], t1[-1])
#    else:
#      print "Got 0 points from new archiver."
    if self.considerOldArch:
      try:
        t2, x2 = self.old_archive_data(pv, time_selection)
      except StandardError as e:
        print "Could not connect to old archiver. {0}".format(e)
        t2, x2 = ([], [])
    else:
      t2, x2 = ([], [])
#    if len(t2) > 0:
#      print "Got {0} points from old archiver from {1} to {2}.".format(len(t2), t2[0], t2[-1])
#    else:
#      print "Got 0 points from old archiver."
    if len(t1) > 0 and len(t2) > 0:
      earliest_new = t1[0]
      earliest_old = t2[0]
      if earliest_old < earliest_new:
        breakpt = len(t2) - 1
        for i in range(len(t2)):
          if t2[i] >= earliest_new:
            breakpt = i - 1
            break
        t = t2[:breakpt] + t1
        x = x2[:breakpt] + x1
        print "Using combined data, {0} points from old archiver and {1} points from new archiver.".format(len(t2), len(t1))
        return t, x
      else:
        print "Using new archiver data"
        return t1, x1
    elif t1:
      print "Using new archiver data"
      return t1, x1
    else:
      print "Using old archiver data"
      return t2, x2

  def new_archive_data(self, pv, time_selection=30, chunk=False):
    pv = urllib.quote(pv, safe="")
    url = urlbase.format(pv)
    startdate, enddate = self._interpret_time_selection(time_selection)
    url += urlfrom.format(self._date_format(startdate))
    url += urlto.format(self._date_format(enddate))
    if not chunk:
      url += nochunk
    printnow("Connecting to new archive ...")
    req = urllib2.urlopen(url, timeout=1)
    printnow(" done\n")
    printnow("Extracting data from new archive ...")
    data = json.load(req)
    t = [datetime.datetime.fromtimestamp(x["secs"]) for x in data[0]["data"]]
    y = [x["val"] for x in data[0]["data"]]
    printnow(" done\n")
    return t, y

  def _date_format(self, datetimeobj):
    d = datetimeobj
    s = date_spec_format.format(d.year, d.month, d.day, d.hour, d.minute, d.second, 0)
    return urllib.quote(s, safe="")

  def _interpret_time_selection(self, time_selection):
    enddate = False
    if type(time_selection)==list:
      startdate=time_selection[0]
      enddate = time_selection[1]
    else:
      startdate=time_selection
    if not enddate:
      enddate = datetime.datetime.now()

    if type(startdate)==str:
      startdate = dateutil.parser.parse(startdate)
    else:
      startdate = datetime.datetime.now()-datetime.timedelta(days=startdate)
    if type(enddate)==str:
      enddate = dateutil.parser.parse(enddate)
    return startdate, enddate

### Methods for interfacing with old archiver ###

  def old_archive_data(self,pv,time_selection=30):
    if not self.considerOldArch:
      print "Not configured to access old archive, must init with hutch."
      return
    startdate, enddate = self._interpret_time_selection(time_selection) 
    self._get_channel(pv)
    printnow("Extracting data from old archive ...")
    time,data = self._get_timeinterval_values_from_arch(startdate,enddate)
    printnow(" done\n")
    if len(time) == 0:
      printnow("WARNING: No data found for {0}.\n".format(pv))
    return time,data

  def _get_channel(self,PV):
    self.present_channel = []
    for tarch in self.arch:
      channel = casi.channel()
      tarch.findChannelByName(PV, channel)
      self.present_channel.append(channel)
  
  def _get_all_channel_values_string(self,channel):
    value = casi.value()
    channel.getFirstValue(value)
    val_string = []
    while value.valid():
      val_string.append(casiTools.formatValue (value))
      value.next()
    return val_string
  
  def _get_timeinterval_values(self,channel,datetime0,datetime1):
    value = casi.value()
    datetime0 = datetime0.strftime('%Y/%m/%d %H:%M:%S')
    try:
      isinarch = channel.getValueAfterTime(datetime0,value)
    except:
      return [],[]
    val = []
    time = []
    while value.valid():
      val.append(value.get())
      time.append(dateutil.parser.parse(value.time()))
      if time[-1]>datetime1:
        break	      
      value.next()
    return time,val 

  def _get_all_values(self):
    val_string = []
    for tchan in self.present_channel:
      val_string.extend(self._get_all_channel_values_string(tchan))
    val_string.sort()
    data=np.zeros([p.np.shape(val_string)[0],2])
    n=0
    for s in val_string:
      ss = s.split('\t')
      d = dateutil.parser.parse(ss[0])
      if ss[1].isdigit():
        v = float(ss[1])
      else:
        v = np.nan
      data[n,:]=[mdates.date2num(d),v]
      n +=1
    return data

  def _get_timeinterval_values_from_arch(self,datetime0,datetime1):
    val = []
    time = []
    #loop over archivers!
    for tchan in self.present_channel:
      ttime,tval = self._get_timeinterval_values(tchan,datetime0,datetime1)
      val.extend(tval)    
      time.extend(ttime)
#    data = zeros([len(time),2])
#    data[:,0]=time
#    data[:,1]=val
#    data = np.sort(data.view([('',data.dtype)]*data.shape[1]),0).view(data.dtype)
    I = np.argsort(time)
    time = np.array(time)
    val = np.array(val)
    val = val[I]
    time = time[I]
    if len(time)==0:
      time,val=self._get_lastvaluebef_from_arch(datetime0)
    return time,val

  def _get_lastvaluebef_from_arch(self,datetime0):
    val = []
    time = []
    nTries=0
    while len(time)==0 and nTries<52:
      for tchan in self.present_channel:
        datetime1=datetime0
        datetime0=datetime1-datetime.timedelta(days=7)
        ttime,tval = self._get_timeinterval_values(tchan,datetime0,datetime1)
        val.extend(tval)    
        time.extend(ttime)
        nTries+=1

    I = np.argsort(time)
    time = np.array(time)
    val = np.array(val)
    val = val[I]
    time = time[I]
    if len(time)>1:
      time=time[-1:]
      val=val[-1:]
    return time,val

#  def _search_pvs(self, pv, num):
#    """
#    Searches through the pvs in the new archiver.
#
#    pv is a string that can contain GLOB wildcards. The server will return
#        pvs that match the expression
#    num is the maximum number of pvs returned.
#    """
#    # No reason to implement this yet when I can't test it...
#    # will involve bplurl + "getAllPVs" + "?pv=pv"
    

def _filtvec(vec,lims):
  filtbool = ((vec>min(lims)) & (vec<max(lims)))
  return filtbool


