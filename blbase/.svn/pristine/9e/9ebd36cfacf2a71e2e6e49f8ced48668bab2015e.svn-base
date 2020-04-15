from blutil import guessBeamline
import pycdb
import pydaq
import os

def getTypeID(mne="Opal1kConfig"):
  a=os.popen("cat /reg/g/pcds/dist/pds/' + guessBeamline() + '/current/build/pdsdata/include/pdsdata/xtc/TypeId.hh | sed -n '/enum Type/,/NumberOf};/p'")
  lines=a.readlines()
  a.close()
  idx = -1
  for i in range(len(lines)):
    if (lines[i].find( "Id_%s" % mne ) > 0 ):
      idx = i-1
      break
  if (idx == -1):
    return None
  else:
    return hex(idx) 

class DaqConfig(object):
  def __init__(self,dbpath=None):
    self.dbpath = dbpath
    self.db = None
    if guessBeamline() == "xpp":
      self.defpalias = "PRINCETON"        # xpp.
    else:
      self.defpalias = "PRINCETON_BURST"  # xcs or mec.

  def create(self, daq=None):
    if self.dbpath is None and daq != None:
      self.dbpath = daq.dbpath()
    # try to append the file name if the path returns a dir
    if os.path.isdir(self.dbpath):
      self.dbpath = os.path.join(self.dbpath, '.configdbrc')
    self.db = pycdb.Db(self.dbpath)

  def unlock(self):
    if self.db is not None:
      self.db.unlock()
      self.db = None

  def __getEvrCfg(self,alias="BEAM"):
    typeid=0x00008 # EVR config
    self.db.sync()
    xtclist=self.db.get(alias=alias,typeid=typeid)
    return xtclist

  def getEvr(self,alias="BEAM"):
    ret = []
    for f in self.__getEvrCfg(alias):
      ret.append( f.get() )
    return ret

  def printEvrRecPulses(self,alias="BEAM"):
    myEvrs = self.getEvr(alias=alias)
    if len(myEvrs)>0:
      for pulse in myEvrs[0]['eventcodes']:
        if pulse['readoutGroup'] > 0:
          print 'we record from pulse: ',pulse['code'],' for group ',pulse['readoutGroup']

  def changeTriggerChan(self,alias="BEAM", channel=0, delay=-1., width=-1., commit=True):
    cfgs = self.__getEvrCfg(alias=alias)
    if (len(cfgs) < 1 ):
      raise RuntimeError("Asked to change from EVR config and could not find it")
    cfg = cfgs[0]
    evr_cfg_pars = cfg.get()
    for pulse in evr_cfg_pars['pulses']:
      print pulse
    if channel > len(evr_cfg_pars['pulses'])-1:
      raise RuntimeError("Asked to change pulse that we have not assigned (idx too large) ")
    change=False
    if delay != -1.:
      evr_cfg_pars['pulses'][channel]['delay']=delay
      change=True
    if width != -1.:
      evr_cfg_pars['pulses'][channel]['width']=width
      change=True
    if not change:
      return

    print '--------------------'
    for pulse in evr_cfg_pars['pulses']:
      print pulse

    cfg.set(evr_cfg_pars)
    ##    self.db.set(alias=alias,xtc=cfg)
    print 'DEBUG: call db.clone....'
    key = self.db.clone(alias)
    print hex(key)
    self.db.substitute(key,cfg)
    if (commit):
      print 'try to commit now....'
      self.db.commit()

    return key

  def copyEvrConfig(self,alias="BEAM", commit=True):
    aliasNew="BEAM" 
    if alias=="BEAM":
      print 'copy settings from BEAM to BEAM_PP (except readout pulse)'
      aliasNew="BEAM_PP" 
    elif alias=="BEAM_PP":
      print 'copy settings from BEAM_PP to BEAM and set readout to code 140'
    else:
      print 'not sure what to do with alias ',alias
      return

    cfgsNew = self.__getEvrCfg(alias=aliasNew)
    if (len(cfgsNew) < 1 ):
      raise RuntimeError("Asked to change to EVR config and could not find it")
    cfgNew = cfgsNew[0]

    cfgs = self.__getEvrCfg(alias=alias)
    if (len(cfgs) < 1 ):
      raise RuntimeError("Asked to change from EVR config and could not find it")
    cfg = cfgs[0]
    evr_cfg_pars = cfg.get()
    for evcode in evr_cfg_pars['eventcodes']:
      if (alias=="BEAM" and evcode['code'] == 95) or (alias=="BEAM_PP" and evcode['code'] == 140):
        evcode['readoutGroup'] = 1
      else:
        evcode['readoutGroup'] = 0

    #now put copy EVR back to the correct alias.
    print 'org cfg: ----------------------'
    #for pulse in cfg.get()['pulses']:
    #  print pulse
    for evcode in cfg.get()['eventcodes']:
      print evcode
    print 'new cfg: ----------------------'
    #for pulse in evr_cfg_pars['pulses']:
    #  print pulse
    for evcode in evr_cfg_pars['eventcodes']:
      print evcode

    cfgNew.set(evr_cfg_pars)

    ##    self.db.set(alias=alias,xtc=cfg)
    print 'DEBUG: call db.clone....'
    key = self.db.clone(aliasNew)
    print hex(key)
    self.db.substitute(key,cfgNew)
    if (commit):
      print 'try to commit now....'
      self.db.commit()

    return key

  def __getPrincetonCfg(self,alias=None):
    if alias == None:
      alias = self.defpalias
    typeid=0x50012 # PrincetonConfig, V5    
    self.db.sync()
    xtclist=self.db.get(alias=alias,typeid=typeid)
    return xtclist

  def getPrinceton(self,alias=None):
    if alias == None:
      alias = self.defpalias
    ret = []
    for f in self.__getPrincetonCfg(alias):
      ret.append( f.get() )
    return ret

  def getPrincetonExpTime(self,alias=None,detn=0):
    if alias == None:
      alias = self.defpalias
    cfgs = self.__getPrincetonCfg()
    if (detn+1 > len(cfgs) ):
      raise RuntimeError("Asked to change Princeton n %d but only %d Princeton(s) are defined" % (detn,len(cfgs)))
    cfg = cfgs[detn]
    cfg_pars = cfg.get()
    return cfg_pars["exposureTime"]

  def setPrincetonExpTime(self,exptime,alias=None,detn=0,commit=True):
    if alias == None:
      alias = self.defpalias
    cfgs = self.__getPrincetonCfg()
    if (detn+1 > len(cfgs) ):
      raise "Asked to change Princeton n %d but only %d Princeton(s) are defined" % (detn,len(cfgs))
    cfg = cfgs[detn]
    cfg_pars = cfg.get()
    cfg_pars["exposureTime"] = exptime
    cfg.set(cfg_pars)
    self.db.set(alias,cfg)
    if (commit):
      self.db.commit()

  def setPrincetonConfig(self,exptime,nshots, config, alias=None, detn=0, commit=True):
    if alias == None:
      alias = self.defpalias
    cfgs = self.__getPrincetonCfg()
    if (detn+1 > len(cfgs) ):
      raise RuntimeError("Asked to change Princeton n %d but only %d Princeton(s) are defined" % (detn,len(cfgs)))
    cfg = cfgs[detn]
    cfg_pars = cfg.get()

    if int(cfg_pars["kineticHeight"]) > 0:
      cfg_pars["numDelayShots"] = cfg_pars["height"] / cfg_pars["kineticHeight"]
      config.bKinetics = True
      config.nshots = int(cfg_pars["numDelayShots"])
      
      fOrgExposureTime = float(cfg_pars["exposureTime"])
      if config.beamRate * fOrgExposureTime >= 1:
        print "!!!Warning!!! Kinetics mode: Princeton %d exposure time %f slower than beam rate %f. Will set to 0.001 second" \
         % (detn, fOrgExposureTime, config.beamRate)
        cfg_pars["exposureTime"] = 0.001
    else:
      config.bKinetics = False
      cfg_pars["exposureTime"] = exptime
      cfg_pars["numDelayShots"] = nshots
    print "setting expousure time to %.3f second" % (float(cfg_pars["exposureTime"]))

    cfg.set(cfg_pars)
##    self.db.set(alias=alias,xtc=cfg)
    key = self.db.clone(alias)
    self.db.substitute(key,cfg)

    if (commit):
      self.db.commit()

    return key
