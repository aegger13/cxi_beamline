import os
from string import ljust
import psp.Pv as Pv
from time import sleep
from blutil import estr, guessBeamline
import numpy as np

def rdEpicsArchiveDaq(fina='epicsArch_test.txt',ignore_labels = False):
  """Reads configuration file that has the description of the different detectors, the default data paths etc."""
  filecontent = dict()
  file = open(fina)
  foundlabel = False

  if ignore_labels:
    tlabel = 'unlabeled_group'
    print tlabel
    foundlabel = True
    tdat = dict()
  while 1:
    line = file.readline()
    if not line:
      break
    if line.strip()=='' or line=='\n':
      continue

    if foundlabel or ignore_labels:
      if line[0] is not '#':
        if line.strip()[0] is '<':
          subfile = line.strip()[1:].strip()
          tpath = os.path.split(fina)[0]
          sfc = rdEpicsArchiveDaq(os.path.join(tpath,subfile),ignore_labels)
          #print sfc 
          #print "\n\n\n\n\n"

          recursive_merge(filecontent,sfc)
        else:
          tPV = line.strip()
          if previousline[0]=='#':
            PVlabel = previousline[1:].strip()
          else:
            PVlabel = 'nolabel-'+line.strip()
          tdat[PVlabel] = line.strip()
          filecontent[tlabel] = tdat

    #label line, keyword to characterize dataset starting next line
    if line[:2]=='#*':
      line = line[2:]
      tlabel = line.strip()
      print tlabel
      foundlabel = True
      tdat = dict()
    previousline = line
  file.close()
  return filecontent


def writeEpicsArchiveDaq(fina='epicsArch_test.txt',data=dict()):
  """Write epics archiver file"""
  dstr = ''
  for label in data.keys():
    dstr += '#* '+label+'\n\n'
    for PVlabel in data[label].keys():
      if not PVlabel[:8]== 'nolabel-':
        dstr += '# ' + PVlabel + '\n'
      dstr += data[label][PVlabel]  + '\n'
    dstr += '\n\n'
  return dstr

def getMotorPvList(motors,filename=None):
  if filename == None:
    bl = guessBeamline()
    blu = bl.upper()
    filename = '/reg/g/pcds/dist/pds/%s/misc/epicsArch_%s_%spython.txt' % (bl, blu, bl)
  PV = dict()
  for motname in motors.__dict__.keys():
    try:
      if motors.__dict__[motname].pvname == 'virtual motor':
        tPV = motors.__dict__[motname].pvpos
      else:
        tPV = motors.__dict__[motname]._Motor__readbackpv
      if not tPV:
        print 'WARNING! Motor %s has no epics PV'%(motname)
      else:
        PV[motname]=tPV
    except:
      print 'WARNING! Unknown problem with  %s'%(motname)
  return PV


def recursive_merge(a,b):
  for key in b.keys():
    if key in a.keys():
      if type(a[key])==type(b[key])==dict:
        recursive_merge(a[key],b[key])
      else:
        print "NB: double dictionary field:"
        print key
        print a[key]
        print b[key]
    else:
      a[key] = b[key]

def check_missing_PVs(motors,daqepicsfile=None, addfile=None,updatelabel = 'missing_motors'):
  if daqepicsfile == None:
    daqepicsfile='/reg/g/pcds/dist/pds/%s/misc/epicsArch.txt' % guessBeamline()
  if addfile == None:
    bl = guessBeamline()
    blu = bl.upper()
    addfile='/reg/g/pcds/dist/pds/%s/misc/epicsArch_%s_%spython.txt' % (bl, blu, bl)
  includedPVs = rdEpicsArchiveDaq(daqepicsfile,ignore_labels=True)
  try:
    includedPVs.pop(updatelabel)
  except:
    pass
  usedPVs = getMotorPvList(motors)
  update = dict()
  for lab,PV in zip(usedPVs.keys(),usedPVs.values()):
    isin = False
    for group in includedPVs:
      if PV in includedPVs[group].values():
        isin = True
    if not isin:
      update[lab]=PV
  pvs = []
  for PV in update.values():
    pvs.append(Pv.Pv(PV))
    pvs[-1].connect()
  sleep(1)
  isavailable = []
  for pv in pvs:
    isavailable.append(pv._Pv__connection_sem.isSet())


  print "Following motor PVs are not in the DAQ archiver, red=not available\n"
  labs = update.keys()
  PVs = update.values()
  labslen = max([len(lab) for lab in labs])
  PVslen = max([len(PV) for PV in PVs])
  for av,lab in zip(isavailable,labs):
    tstr = '   '+ljust(lab,labslen,' ')+':  ' + update[lab]
    if not av:
      tstr = estr(tstr,color='red')
    print tstr
  print 'Would you like to write these to '
  print '%s ?'%addfile
  print 'y(es) / n(o) / o(nly available PVs) '
  inp = raw_input()
  if inp=='y':
    writegroup = dict()
    writegroup[updatelabel] = update
    writeEpicsArchiveDaq(daqepicsfile,writegroup)
  elif inp=='o':
    writegroup = dict()
    avupdate = dict()
    for ia,lab in zip(isavailable,labs):
      if ia:
        avupdate[lab] = update[lab]
    writegroup[updatelabel] = avupdate
    return writeEpicsArchiveDaq(daqepicsfile,writegroup)








  



