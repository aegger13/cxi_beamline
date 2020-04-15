""" Utilities to display laser lock quality """

import psp.Pv as Pv
import numpy as n
import scipy as s
from matplotlib.pyplot import *
from time import sleep, mktime, strftime, strptime
import datetime
import epicsarchive

epicsarchive_cds = epicsarchive.epicsarchive('cds', start_year=2014)

def TimingSystemLockPlot():
  alldiff=Pv.get("LAS:FS3:alldiff_fs:Hist:LAST_N")  
  t=n.linspace(0,10,256)
  uniq=[]
  for i in alldiff:
    if i not in uniq:
      uniq.append(i)
  
  N=len(uniq)
  std=n.std(uniq)
  fwhm=2.3548*std
  ion()
  fig=figure(50,figsize=(12,6))
  clf()

  subplot(121)
  plot(t,alldiff,'b.-')
  ylabel('FS3:alldiff (fs)')
  xlabel('seconds')
  title('XPP Oscillator Phase Lock')
  ylim(1.25*min(alldiff),1.25*max(alldiff))

  subplot(122)
  hist(uniq,15,histtype='bar')
  ax=fig.add_subplot(122)
  ylabel('Samples')
  xlabel('FS3:alldiff (fs)')
  title('XPP Oscillator Phase Lock')
  xlim(-500,500)
  tight_layout()
  text(0.05,0.87,' sdev=%3.0f fs\nfwhm=%3.0f fs\n       n=%d' %(std,fwhm,N), transform=ax.transAxes,bbox={'facecolor':'white','pad':15})
  draw()

def TimingSystemPhaseLockMonitor(t=2):
  """ Monitors the FS3 alldiff signal
      t is the refresh time in seconds
      Ctrl+c will exit monitoring
  """
  try:
    while True:
      TimingSystemLockPlot()
      print "Phase lock monitor running. Press CTRL-c to halt."
      sleep(t)
  except KeyboardInterrupt:
    print "\n Ctrl + c pressed. Stopped FS3 alldiff monitor."

def LeCroyDriftMonitor(date=None):
  """ Drift monitor plot from the LeCroy drift monitor
      file written in ~xppopr/drift_monitor_hutch/
      folder
  """

  path = '/reg/neh/operator/xppopr/drift_monitor_hutch/'
  if date != None:
    filename = path + 'timing_drift_monitor_'+date+'.out'
  else:
    filename = path + 'timing_drift_monitor_'+strftime('%Y%m%d')+'.out'
  fid = open(filename)
  
  ind = []
  date = []
  las = []
  RF = []
  phaseshifter = []
  micrapiezo = []
  micratweeter = []
  temp2 = []
  temp3 = []

  lines = fid.readlines()
  for l in lines:
    a = l.split()
    ind.append(n.float(a[0]))
    date.append(mktime(strptime(a[1], "%Y%m%d_%H%M%S")))
    las.append(n.float(a[5])-7.06e-9)
    RF.append(n.float(a[2])+24.479e-9)
    
    phaseshifter.append(n.float(a[8])-7.930e-9)
    micrapiezo.append(n.float(a[9]))
    micratweeter.append(n.float(a[10]))

    temp2.append(n.float(a[12]))
    temp3.append(n.float(a[13]))

  lasCorr = n.array(las)-n.array(RF)-n.array(phaseshifter)
  ion()
  fig = figure(51)
  clf()
  plot(date, las, 'r')
  plot(date, RF, 'b')
  plot(date, phaseshifter, 'y')
  plot(n.array(date), lasCorr, 'g')
  draw()

def CheckPhaseCavity(t=1):
  t1, c1 = epicsarchive_cds.pv_archive_data('UND:R02:IOC:10:BAT:FitTime1',t)

  t2, c2 = epicsarchive_cds.pv_archive_data('UND:R02:IOC:10:BAT:FitTime2',t)
  ion()
  fig = figure(52)
  clf()
  plot(t1,c1-5,'.g')
  plot(t2,c2,'.r')
  ylim(-2, 3)
  xlabel('time')
  ylabel('ebeam time (ps)')
  draw()

def MonitorPhaseCavity(t=2):
  """ Monitors the phase cavity measurement
      t is the refresh time in seconds
      Ctrl+c will exit monitoring
  """
  try:
    while True:
      CheckPhaseCavity(0.002)
      print "Checking the phase cavity recent history. Press CTRL-c to halt."
      sleep(t)
  except KeyboardInterrupt:
    print "\n Ctrl + c pressed. Stopped phase cavity monitor."

