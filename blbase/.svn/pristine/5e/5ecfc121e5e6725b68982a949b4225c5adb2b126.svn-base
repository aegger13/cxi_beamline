#!/bin/env python

import os
import sys
import getopt
import time
import datetime
import pydaq
import pycdb
import blutil
import socket
import traceback
import eventsequencer
from blinst import linac
from blbase.scan import AScan, A2Scan, DScan, D2Scan


class SeqConfig(object):
  def __init__(self, pvSeq, iSeqId, eventCameraOpen, eventShutterOpenClose, eventDaqReadout, eventDaqSlowReadout, beamDbKey, simDbKey, readoutGrps, shutterInit=None):
    self.pvSeq = pvSeq
    self.iSeqId = iSeqId
    self.eventCameraOpen = eventCameraOpen
    self.eventShutterOpenClose = eventShutterOpenClose
    self.eventDaqReadout = eventDaqReadout
    self.eventDaqSlowReadout = eventDaqSlowReadout
    self.beamDbKey = beamDbKey
    self.simDbKey = simDbKey
    self.readoutGrps = readoutGrps
    self.shutterInit = shutterInit

  def __repr__(self):
    return '%s(pvSeq=%s, iSeqId=%s, eventCameraOpen=%s, eventShutterOpenClose=%s, eventDaqReadout=%s, eventDaqSlowReadout=%s, beamDbKey=%s, simDbKey=%s, readoutGrps=%s)' % (
        self.__class__.__name__,
        self.pvSeq, self.iSeqId,
        self.eventCameraOpen,
        self.eventShutterOpenClose,
        self.eventDaqReadout,
        self.eventDaqSlowReadout,
        self.beamDbKey,
        self.simDbKey,
        self.readoutGrps
      )


class MccBurst(object):
  def __init__(self, bSimMode, seq):
    self.bSimMode         = bSimMode
    self.bMccBurstRunning = False
    self.seq   = seq
    self.linac = linac.Linac()

  def isLegalBeamRate(self, fRate):
    return self.linac.islegalrate(fRate)

  def mccBurstCheckInit(self):
    self.bMccBurstRunning = self.linac.isburstenabled()
    print "Mcc Burst Mode: %s" % ("Yes" if self.bMccBurstRunning else "No")

  def mccBurstCheckStatusChange(self):
    if self.bSimMode:
      return False
    bMccBurstCheck = self.linac.isburstenabled()
    if bMccBurstCheck != self.bMccBurstRunning:
      print "Original Burst mode: %s  Current: %s" % (("Yes" if self.bMccBurstRunning else "No"), ("Yes" if bMccBurstCheck else "No"))
      return True
    return False

  def mccBurstSetNumShot(self, iNumShots, fBurstRate):
    if self.bSimMode:
      return False
    print "Settings Mcc Burst Shot %d rate %f" % (iNumShots, fBurstRate)
    if not self.seq.is_beam_owner():
      self.linac.set_nburst(iNumShots)  # Set # of bursts test mode 
    else:
      self.linac.set_nburst(iNumShots)  # Set # of bursts
    self.mccBurstSetRate(fBurstRate)
    return 0

  def mccBurstSetRate(self, fBurstRate):
    if self.bSimMode:
      return True
    if not self.seq.is_beam_owner():
      print "Settings Test Burst Rate %f" % fBurstRate
      self.linac.set_testburst_rate(fBurstRate)
    else:
      print "Settings Mcc Burst Rate %f" % fBurstRate
      self.linac.set_burst_rate(fBurstRate)
    return 0

  def mccBurstIsComplete(self):
    if self.bSimMode:
      return True
    return not self.linac.isshooting()

  def mccBurstCount(self):
    if self.bSimMode:
      return 0
    if not self.seq.is_beam_owner():
      return int(self.linac.get_test_nburst())
    else:
      return int(self.linac.get_nburst())

  def mccBurstStart(self, wait=True):
    self.linac.start_burst()
    if wait:
      self.linac.wait_for_shot()


class SlowCamera(object):
  def __init__(self, iNumShot, fExpDelay, fPostDelay, iOpenDelay, fBurstRate, bSimMode, bShutterMode, seqConfig, daq=None, daqcfg=None):
    self.iNumShot   = iNumShot
    self.fExpDelay  = fExpDelay
    self.fPostDelay = fPostDelay
    self.fBurstRate = fBurstRate
    self.bSimMode     = (bSimMode or bShutterMode)  # shutter mode use the same sequence as sim mode
    self.bShutterMode = bShutterMode
    self.seqConfig = seqConfig
    self.seq = eventsequencer.EventSequencer(local_iocbase=self.seqConfig.pvSeq,sequence_group=self.seqConfig.iSeqId)

    self.daq              = daq
    self.daqcfg           = daqcfg
    self.bBeginCycle      = False
    self.iNumTotalImage   = 0
    self.mccBurst         = MccBurst(self.bSimMode, self.seq)

    if self.daq is None:
      self.daq_host         = socket.gethostname()
      print "Host: %s" % self.daq_host
      self.daq_platform      = 0 # 0 for MEC, 1 for XCS

    self.iSlowCamOpenDelay = iOpenDelay # unit: 120Hz

    self.eventCameraOpen = self.seqConfig.eventCameraOpen
    self.eventShutterOpenClose = self.seqConfig.eventShutterOpenClose
    self.eventDaqReadout = self.seqConfig.eventDaqReadout
    self.eventDaqSlowReadout = self.seqConfig.eventDaqSlowReadout
    if not self.bShutterMode:
      self.eventShutterOpenClose = 0
    # check if using readout groups and the fast DAQ readout code is a burst one
    if self.eventDaqReadout == 0:
      self.burstReadout = True
    else:
      self.burstReadout = False

  def getEventNum(self):
    return self.daq.eventnum()

  def setCameraControlSequence(self):
    print "Settings camera control sequence...\n"

    iBurstInterval    = int(120 / self.fBurstRate)
    iInitDelay        = (iBurstInterval - self.iSlowCamOpenDelay) % iBurstInterval
    if self.bShutterMode:
      iShutterOpenDelay = 2 # for both single shot and burst mode
      iInitToShutter    = self.iSlowCamOpenDelay - iShutterOpenDelay

      event_codes      = [self.eventCameraOpen, self.eventShutterOpenClose, 0                  , self.eventDaqReadout]
      beam_delays      = [iInitDelay          , iInitToShutter            , iShutterOpenDelay-1, 1                   ]
      burst_requests   = [0                   , 0                         , self.iNumShot      , 0                   ]

      if self.iNumShot > 1:
        event_codes   += [self.eventDaqReadout] * (self.iNumShot-2)
        beam_delays   += [iBurstInterval      ] * (self.iNumShot-2)

        event_codes   += [self.eventShutterOpenClose, self.eventDaqReadout]
        beam_delays   += [iBurstInterval-1          , 1                   ]

      if self.seqConfig.readoutGrps:
        event_codes   += [self.eventDaqSlowReadout]
        beam_delays   += [0]

      burst_requests    += [0]* ( len(event_codes) - len(burst_requests) )
      fiducial_delays    = [0]* len(event_codes)
    else:
      iBurstReqDelay  = 1
      iInitToBurstReq = self.iSlowCamOpenDelay - iBurstReqDelay
    
      event_codes      = [self.eventCameraOpen, 0              ]
      beam_delays      = [iInitDelay          , iInitToBurstReq]
      if self.bSimMode:
        if not self.seq.is_beam_owner() or self.burstReadout:
          burst_requests  = [0, self.iNumShot]
        else:
          burst_requests  = [0, 0            ]
      else:
        burst_requests    = [0, self.iNumShot]

      if self.burstReadout:
        if self.seqConfig.readoutGrps:
          event_codes   += [self.eventDaqSlowReadout]
          beam_delays   += [self.iNumShot*iBurstInterval]
      else:
        event_codes += [self.eventDaqReadout]
        beam_delays += [iBurstReqDelay      ]

        if self.iNumShot > 1:
          event_codes   += [self.eventDaqReadout] * (self.iNumShot-1)
          beam_delays   += [iBurstInterval      ] * (self.iNumShot-1)

        if self.seqConfig.readoutGrps:
          event_codes   += [self.eventDaqSlowReadout]
          beam_delays   += [0]

      burst_requests    += [0]* ( len(event_codes) - len(burst_requests) )
      fiducial_delays    = [0]* len(event_codes)

    nstep = 0 # number of lines in the sequence
    for bc, db, df, br in zip(event_codes, beam_delays, fiducial_delays, burst_requests):
      self.seq.setstep(nstep, bc, db, df, br, verbose=True)
      nstep += 1
    self.seq.setnsteps(nstep)
    self.seq.update() # push the changes
    return 0

  def init(self, controls = None, bDaqBegin = True):
    while True:
      fBeamFullRate = self.seq.beamrate();
      if fBeamFullRate == 0.5 or float(int(fBeamFullRate)) == fBeamFullRate:
        break

    if not self.bSimMode:
      if not (self.mccBurst.isLegalBeamRate(fBeamFullRate)):
        print "!!! Beam rate %g is not stable, please wait for beam to stablize and run the script again" % (fBeamFullRate)
        return 1
      self.mccBurst.mccBurstCheckInit()

    if self.fBurstRate == -1:
      self.fBurstRate = fBeamFullRate

    if not (self.fBurstRate in self.seq.dictRateToSyncMarker):
      print "!!! Burst rate %g not supported" % (self.fBurstRate)
      return 1

    self.seq.modeOnce() # PlayMode = Once
    self.seq.setSyncMarker(self.fBurstRate)

    self.seq.getSyncMarker() # caget bug: need to get twice to have latest value
    print "\n## Beam rate = %g HZ, Sync marker = %g HZ" % (fBeamFullRate, self.seq.getSyncMarker())

    if not self.bSimMode:
      if not self.seq.is_beam_owner():
        if self.fBurstRate == 60:
          print "!!! Test Burst rate %g is not supported by MCC" % (self.fBurstRate)
          return 1
        self.mccBurst.mccBurstSetRate(self.fBurstRate)
      elif self.fBurstRate == fBeamFullRate:
        self.mccBurst.mccBurstSetRate(0)
      elif self.fBurstRate < fBeamFullRate:
        if self.fBurstRate == 60:
          print "!!! Burst rate %g is not supported by MCC" % (self.fBurstRate)
          return 1
        self.mccBurst.mccBurstSetRate(self.fBurstRate)
      else:
        print "!!! Burst rate %g is faster than Beam rate %g" % (self.fBurstRate, fBeamFullRate)
        return 1

    print "## Multiple shot: %d" % (self.iNumShot)

    # Exposure Time =
    #     camear open (clean CCD) delay ( self.iSlowCamOpenDelay: 0 for PI, 5*120Hz for FLI)
    #     + manual sleep (fExpDelay)
    #     + exposure Time ((self.iNumShot / self.fBurstRate) second)
    #   = 0.0 + max(1, self.iSlowCamOpenDelay)/120.0 + (self.iNumShot / self.fBurstRate) + fExpDelay  second
    self.fExposureTime = 0.0 + self.iSlowCamOpenDelay/120.0 + self.fExpDelay + self.iNumShot / float(self.fBurstRate)

    if self.daq is None:
      print "CREATE DAQ CONTROL OBJECT"
      self.daq = pydaq.Control(self.daq_host, self.daq_platform)
    try:
      print "daq connect...",
      sys.stdout.flush()
      self.daq.connect() # get dbpath and key from DAQ
      print " done."
    except:
      print "!! daq.connect() failed"
      print "!! Possibly because 1. DAQ devices has NOT been allocated"
      print "!!               or 2. You are running DAQ control GUI in remote machines"
      print "!! Please check 1. DAQ is in good state and re-select the devices"
      print "!!              2. If the restart script actually runs DAQ in another machine"
      print "ERROR",sys.exc_info()[0]
      return 1

    if self.bSimMode:
      self.alias = self.seqConfig.simDbKey
    else:
      self.alias = self.seqConfig.beamDbKey

    if self.daq.dbalias() != self.alias:
      print "!!! the current DAQ config type is %s" % (self.daq.dbalias())
      print "!!! please switch to %s to run this script" % (self.alias)

      print "daq disconnect...",
      sys.stdout.flush()
      self.daq.disconnect()
      print " done."
      return 2

    if not self.bShutterMode and not self.bSimMode and not self.seq.is_beam_owner():
      print "!!! simulation mode is set to %s" % self.bSimMode
      print "!!! beamowner is set to %s" % self.seq.is_beam_owner()
      print "!!! can't run burst mode when not the beam owner!"

      print "daq disconnect...",
      sys.stdout.flush()
      self.daq.disconnect()
      print " done."
      return 2

    if not self.bShutterMode and self.bSimMode and self.burstReadout and self.seq.is_beam_owner():
      print "!!! simulation mode is set to %s" % self.bSimMode
      print "!!! beamowner is set to %s" % self.seq.is_beam_owner()
      print "!!! can't run using burst event codes in sim mode when the beam owner!"

      print "daq disconnect...",
      sys.stdout.flush()
      self.daq.disconnect()
      print " done."
      return 2

    print "CONFIGURE DAQ"
    if controls is None:
      iFail = self.configure(controls=[])
    else:
      iFail = self.configure(controls=controls)
    if iFail != 0:
      print "daq disconnect...",
      sys.stdout.flush()
      self.daq.disconnect()
      print " done."
      return 3

    if self.bShutterMode and self.seqConfig.shutterInit is not None:
      try:
        self.seqConfig.shutterInit(self.iNumShot)
      except:
        print "Shutter Init Failed"
        return 4

    print "SET CAMERA CONTROL SEQUENCE"
    self.setCameraControlSequence()

    self.iNumTotalImage = 0

    print "## Please make sure"
    if not self.bSimMode:
      print "##   - MCC has switched to Burst Mode,"
    print "##   - Andor/Princeton camera is selected (if you need it),"
    print "##   - chiller is running and the cooling temperature is set properly."

    if bDaqBegin:
      # cpo changed this line
      self.beginCycle(controls)
    return 0

  def configure(self, controls = None):
    if self.daqcfg is None:
      cdb = pycdb.Db(self.daq.dbpath())
    else:
      cdb = self.daqcfg.db
    newkey = cdb.get_key(self.alias)
    print "db path = %s  key = 0x%x" % (self.daq.dbpath(), self.daq.dbkey())

    if hasattr(self.daq, 'partition'):
      partition = self.daq.partition()
    else:
      partition = self.daq.getPartition()
    lAllocatedPrinceton = []
    lAllocatedFli       = []
    lAllocatedAndor     = []
    lAllocatedPimax     = []
    for daqNode in partition['nodes']:
      # example of daqNode: {'record': True, 'phy': 256L, 'id': 'NoDetector-0|Evr-0', 'readout': True}
      phy = daqNode['phy']
      devId = ((phy & 0x0000FF00) >> 8)
      devNo = (phy & 0x000000FF)
      if devId == 6: # Princeton
        lAllocatedPrinceton.append((phy,devNo))
      elif devId == 23:
        lAllocatedFli.append((phy,devNo))
      elif (devId == 25) or (devId == 38):
        lAllocatedAndor.append((phy,devNo))
      elif devId == 32:
        lAllocatedPimax.append((phy,devNo))

    fMaxReadoutTime = 0
    lSpeedTable     = [ 0.1, 1, 0, 0, 1, 2 ]
    for cam_index,(phy,iCamera) in enumerate(lAllocatedPrinceton):
      lXtcPrinceton = cdb.get(key=newkey,src=phy)
      print "Princeton %d (detector id: 0x%x)" % (iCamera, phy)
      if len(lXtcPrinceton) != 1:
        print "!! Error: Princeton %d should only have one config, but found %d configs" % (iCamera, len(lXtcPrinceton))
        continue
      xtc              = lXtcPrinceton[0]
      configPrinceton  = xtc.get()
      fOrgExposureTime = float(configPrinceton['exposureTime'])
      width            = configPrinceton['width']
      height           = configPrinceton['height']
      speed            = configPrinceton['readoutSpeedIndex']
      code             = configPrinceton['exposureEventCode']
      kineticHeight    = configPrinceton['kineticHeight']

      configPrinceton['exposureEventCode'] = self.eventCameraOpen

      if speed < 0 or speed > len(lSpeedTable) or lSpeedTable[speed] == 0:
        #print "*** Princeton %d configuation error: Unknown speed setting %d\n"\
        #  "Please check the readout speed index in the configuration window\n"\
        #  % (iCamera, speed)
        speed = 1
        #return 1

      #fReadoutTime = 4.7 * width * height / ( lSpeedTable[speed] * 2048 * 2048 )
      fReadoutTime = 4.7 / lSpeedTable[speed]
      if fReadoutTime > fMaxReadoutTime:
        fMaxReadoutTime = fReadoutTime

      print "  W %d H %d speed %d code %d readout %.3f" % (width, height, speed, configPrinceton['exposureEventCode'], fReadoutTime)

      if kineticHeight == 0:
        print "  Exposure time (Original) [%d]: %.3f s" % (iCamera, fOrgExposureTime)
        configPrinceton['exposureTime']     = self.fExposureTime + cam_index
        print "  Exposure time (New)      [%d]: %.3f s" % (iCamera, configPrinceton['exposureTime'])
      else:
        if height % kineticHeight != 0:
          print "!!! Princeton %d Illegal kinetics height %d (Image height %d)" \
           % (iCamera, kineticHeight, height)
          return 2
        iNumKineticShot = height / kineticHeight
        print "  Kinetic mode: shots = %d" % (iNumKineticShot)
        if self.fBurstRate * fOrgExposureTime >= 1:
          print "!!! Princeton %d exposure time %f slower than beam rate %f. Not okay for kinetics mode" \
           % (iCamera, fOrgExposureTime, self.fBurstRate)
          return 2
          self.iNumShot = iNumKineticShot

      if self.seqConfig.readoutGrps:
        configPrinceton['numDelayShots'] = 1
      else:
        configPrinceton['numDelayShots'] = self.iNumShot
      print "  Number of Delayed Shots: [%d]: %d" % (iCamera, configPrinceton['numDelayShots'])

      xtc.set(configPrinceton)      
      cdb.set(xtc = xtc, alias = self.alias)

    lSpeedTable     = [ 0.2, 1 ]
    for cam_index,(phy,iCamera) in enumerate(lAllocatedFli):
      lXtcFli = cdb.get(key=newkey,src=phy)
      print "Fli %d (detector id: 0x%x)" % (iCamera, phy)
      if len(lXtcFli) != 1:
        print "!! Error: Fli %d should only have one config, but found %d configs" % (iCamera, len(lXtcFli))
        continue
      xtc              = lXtcFli[0]
      configFli        = xtc.get()
      fOrgExposureTime = float(configFli['exposureTime'])
      width            = configFli['width']
      height           = configFli['height']
      speed            = configFli['readoutSpeedIndex']
      code             = configFli['exposureEventCode']

      configFli['exposureEventCode'] = self.eventCameraOpen

      if speed < 0 or speed > len(lSpeedTable) or lSpeedTable[speed] == 0:
        print "*** Fli %d configuation error: Unknown speed setting %d\n"\
          "Please check the readout speed index in the configuration window\n"\
          % (iCamera, speed)
        return 1

      #fReadoutTime = 4.3 * width * height / (4096 * 4096)
      fReadoutTime = 4.3 / lSpeedTable[speed]
      if fReadoutTime > fMaxReadoutTime:
        fMaxReadoutTime = fReadoutTime

      print "  W %d H %d speed %d code %d readout %.3f" % (width, height, speed, configFli['exposureEventCode'], fReadoutTime)
      print "  Exposure time (Original) [%d]: %.3f s" % (iCamera, fOrgExposureTime)
      configFli['exposureTime']     = self.fExposureTime + cam_index
      print "  Exposure time (New)      [%d]: %.3f s" % (iCamera, configFli['exposureTime'])

      if self.seqConfig.readoutGrps:
        configFli['numDelayShots'] = 1
      else:
        configFli['numDelayShots'] = self.iNumShot
      print "  Number of Delayed Shots: [%d]: %d" % (iCamera, configFli['numDelayShots'])

      xtc.set(configFli)
      cdb.set(xtc = xtc, alias = self.alias)

    lSpeedTable     = [ 1, 0.6, 0.2, 0.01 ]
    for cam_index,(phy,iCamera) in enumerate(lAllocatedAndor):
      lXtcAndor = cdb.get(key=newkey,src=phy)
      print "Andor %d (detector id: 0x%x)" % (iCamera, phy)
      if len(lXtcAndor) != 1:
        print "!! Error: Andor %d should only have one config, but found %d configs" % (iCamera, len(lXtcAndor))
        continue
      xtc              = lXtcAndor[0]
      configAndor      = xtc.get()
      fOrgExposureTime = float(configAndor['exposureTime'])
      width            = configAndor['width']
      height           = configAndor['height']
      speed            = configAndor['readoutSpeedIndex']
      code             = configAndor['exposureEventCode']

      configAndor['exposureEventCode'] = self.eventCameraOpen

      if speed < 0 or speed > len(lSpeedTable) or lSpeedTable[speed] == 0:
        print "*** Andor %d configuation error: Unknown speed setting %d\n"\
          "Please check the readout speed index in the configuration window\n"\
          % (iCamera, speed)
        return 1

      fReadoutTime = 1.1 / lSpeedTable[speed]
      if fReadoutTime > fMaxReadoutTime:
        fMaxReadoutTime = fReadoutTime

      print "  W %d H %d speed %d code %d readout %.3f" % (width, height, speed, configAndor['exposureEventCode'], fReadoutTime)
      print "  Exposure time (Original) [%d]: %.3f s" % (iCamera, fOrgExposureTime)
      configAndor['exposureTime']     = self.fExposureTime + cam_index
      print "  Exposure time (New)      [%d]: %.3f s" % (iCamera, configAndor['exposureTime'])

      if self.seqConfig.readoutGrps:
        configAndor['numDelayShots'] = 1
      else:
        configAndor['numDelayShots'] = self.iNumShot
      print "  Number of Delayed Shots: [%d]: %d" % (iCamera, configAndor['numDelayShots'])

      xtc.set(configAndor)
      cdb.set(xtc = xtc, alias = self.alias)

    for cam_index,(phy,iCamera) in enumerate(lAllocatedPimax):
      lXtcPimax = cdb.get(key=newkey,src=phy)
      print "Pimax %d (detector id: 0x%x)" % (iCamera, phy)
      if len(lXtcPimax) != 1:
        print "!! Error: Pimax %d should only have one config, but found %d configs" % (iCamera, len(lXtcPimax))
        continue
      xtc              = lXtcPimax[0]
      configPimax      = xtc.get()
      fOrgExposureTime = float(configPimax['exposureTime'])
      width            = configPimax['width']
      height           = configPimax['height']
      speed            = configPimax['readoutSpeed']
      code             = configPimax['exposureEventCode']

      configPimax['exposureEventCode'] = self.eventCameraOpen

      fReadoutTime = 1 / speed
      if fReadoutTime > fMaxReadoutTime:
        fMaxReadoutTime = fReadoutTime

      print "  W %d H %d speed %d code %d readout %.3f" % (width, height, speed, configPimax['exposureEventCode'], fReadoutTime)
      print "  Exposure time (Original) [%d]: %.3f s" % (iCamera, fOrgExposureTime)
      configPimax['exposureTime']     = self.fExposureTime + cam_index
      print "  Exposure time (New)      [%d]: %.3f s" % (iCamera, configPimax['exposureTime'])

      if self.seqConfig.readoutGrps:
        configPimax['numIntegrationShots'] = 1
      else:
        configPimax['numIntegrationShots'] = self.iNumShot
      print "  Number of Integration Shots: [%d]: %d" % (iCamera, configPimax['numIntegrationShots'])

      xtc.set(configPimax)
      cdb.set(xtc = xtc, alias = self.alias)
     
    cdb.commit()
    newkey = cdb.get_key(self.alias)
    cdb.unlock()

    print "setting exposure time to %.2f s" % (self.fExposureTime)

    #
    #    self.daq.configure(events=options.events,
    #                  controls=[('EXAMPLEPV1',0),('EXAMPLEPV2',0)],
    #                  monitors=[('BEAM:LCLS:ELEC:Q',options.qbeam,1.)])
    #
    #    self.daq.configure(record=do_record,
    #                  events=options.events,
    #                  controls=[('EXAMPLEPV1',0),('EXAMPLEPV2',0)])
    print "CONTROLS LIST:",controls
    print "daq configure...",
    sys.stdout.flush()
    # cpo changed this line
    #print "()()()\n",controls
    if controls is None :
      self.daq.configure(key=newkey, events=0, controls=[])
    else :
      self.daq.configure(key=newkey, events=0, controls=controls)
    print " done."

    return 0

  def getMoreImages(self, iNumImage, x_motor=None, token_x=None, destination=None, delayT=None):
    for iImage in xrange(iNumImage):
      if (not self.bShutterMode) and self.mccBurst.mccBurstCheckStatusChange():
        print "Burst Mode status changed"
        break

      timeBeforeImage = time.time()

      print "# Image %d/%d (%d Shots) [total images: %d]" % (1+iImage, iNumImage, self.iNumShot, self.iNumTotalImage)
      iEventStart = self.getEventNum()

      timeAfterImageBegin = time.time()

      if x_motor is not None:
        # should be close to the 1st event
        print "Scan on X starts now from %s mm to %s mm" % (token_x, destination)
        print "DAQ starts recording 1st event %s s after motor started." % delayT
        print "Time right before moving motor ", datetime.datetime.now().time()
        x_motor.mv( destination )           
        
        # user specficy delay in distance
        time.sleep(delayT)
        print "Motor position before first DAQ event:" , x_motor.wm(), " mm"

      self.seq.start() # PlayCtrl = Play


      timeAfterPlay = time.time()
      print "###################### Event sequence played at:", timeAfterPlay

      time.sleep(0.02)
      self.seq.wait()

      timeBeforeBurst = time.time()

      if not self.bShutterMode and self.seq.is_beam_owner():
        time.sleep(0.02)
        while True:
          if self.mccBurst.mccBurstIsComplete():
            break
          iNumBurstCount = self.mccBurst.mccBurstCount()
          print "Burst count: %d / %d\r" % (iNumBurstCount, self.iNumShot),
          sys.stdout.flush()
          time.sleep(0.05)

      timeAfterBurstComplete = time.time()

      print "Waiting for device readout... "
      if self.fPostDelay > 0:
        print "Sleeping for %.1f seconds... " % (self.fPostDelay),
        sys.stdout.flush()
        time.sleep(self.fPostDelay) # post delay: wait for DAQ to really ends if data valume is too large
        print "done."

      print "Waiting for DAQ event: %d" % self.iNumShot
      time.sleep(1)

      while True:
        eventnum = self.getEventNum()
        if eventnum >= iEventStart + self.iNumShot:
          if x_motor is not None:
            print "Time after DAQ ", datetime.datetime.time(datetime.datetime.now())
            print "Motor position after last DAQ event:" , x_motor.wm(), " mm"
          break
        print "DAQ event: %d / %d\r" % (eventnum, iEventStart + self.iNumShot),
        sys.stdout.flush()
        time.sleep(0.05)
      print "                           \r",

      timeEndImage = time.time()
      print "time (sec): Image %.2f Begin %.2f SeqPvSet %.2f PlaySeq %.2f Burst %.2f End %.2f" %\
       (timeEndImage-timeBeforeImage,  \
        timeAfterImageBegin - timeBeforeImage, timeAfterPlay - timeAfterImageBegin, \
        timeBeforeBurst - timeAfterPlay, timeAfterBurstComplete - timeBeforeBurst,  \
        timeEndImage-timeAfterBurstComplete )

      self.iNumTotalImage += 1
    # end: for iImage in xrange(iNumImage)

  def numTotalImage(self):
    return self.iNumTotalImage

  # cpo changed this line
  def beginCycle(self,controls = None, events=0):
    print "BEGINCYCLE"
    if self.daq == None:
      return
    if self.bBeginCycle:
      return

    try:
      print "daq begin...",
      sys.stdout.flush()
      # cpo changed this line
      print '---', controls
      if controls is None :
        self.daq.begin(events=events,controls=[])
      else:
        self.daq.begin(events=events,controls=controls) # run until we call daq.stop()
      #self.daq.begin(events=0) # run until we call daq.stop()
      print " done."
    except :      
      print "daq.begin() timeout"
      print "ERROR:",sys.exc_info()[0]
      return

    self.bBeginCycle = True
    time.sleep(0.5) # wait for EVR to enable. Not needed for new DAQ release

  def endCycle(self):
    print "ENDCYCLE"
    if self.daq == None:
      return
    if not self.bBeginCycle:
      return

    try:
      print "daq stop...",
      sys.stdout.flush()
      self.daq.stop()
      print " done."
    except:
      print "daq.stop() timeout"
      print "ERROR:",sys.exc_info()[0]

    #try:
    #  print "daq end... waiting for daq to finish...",
    #  sys.stdout.flush()
    #  self.daq.end()
    #  print " done."
    #except:
    #  print " done (already stopped)."
    #  print "ERROR:",sys.exc_info()[0]
    #  return

    self.bBeginCycle = False

  def nextCycle(self,controls = None):
    print "NEXTCYCLE"
    if self.daq == None:
      return
    self.endCycle()
    # cpo changed this line
    self.beginCycle(controls)

  def deinit(self):
    if self.daq == None:
      return

    self.endCycle()

    try:
      print "daq disconnect...",
      sys.stdout.flush()
      self.daq.disconnect()
      print " done."
    except:
      print "daq.disconnect() timeout"
      print "ERROR:",sys.exc_info()[0]
      return

class SlowCameraInteractive(object):
  def __init__(self, seqConfig, daq=None, daqcfg=None, controls=None):
    self.seqConfig = seqConfig
    self.daq = daq
    self.daqcfg = daqcfg
    if controls is None:
      self.controls = []
    else:
      self.controls = controls

  def run(self, iNumShot, fExpDelay, fPostDelay, iOpenDelay, fBurstRate, bSimMode, bShutterMode):
    slowcamDaq = SlowCamera(iNumShot, fExpDelay, fPostDelay, iOpenDelay, fBurstRate, bSimMode, bShutterMode, self.seqConfig, self.daq, self.daqcfg)
    #iFail = slowcamDaq.init()
    iFail = slowcamDaq.init(controls=self.controls,bDaqBegin=False)
    if iFail != 0:
      return 1

    try:
      while True:
        #
        #  Wait for the user to continue
        #
        print('--Enter a number + <Enter> to get more images, or just Hit <Enter> to end run and exit--')
        sMoreImage = raw_input("> ")

        try:
          iMoreImage = int(sMoreImage)
        except:
          iMoreImage = 0

        if iMoreImage <= 0:
          break

        print("Will get %d more images..." % iMoreImage)
        slowcamDaq.beginCycle([])
        slowcamDaq.getMoreImages(iMoreImage)
        slowcamDaq.endCycle()
        # go to next loop to get more Images
      #end of while True:

      daq = slowcamDaq.daq
      print "# (If Record Run is ON) Experiment %d Run %d (%d images)" % (daq.experiment(),daq.runnumber(), slowcamDaq.numTotalImage())
      slowcamDaq.deinit()
      time.sleep(0.5)
    except:
      print "\n!!! Script exits abnormally (may be interrupted by user)"
      print "ERROR:",sys.exc_info()[0]
      daq = slowcamDaq.daq
      slowcamDaq.deinit()
      time.sleep(0.5)

    return 0

class SlowCameraManager(object):
  """
  Manages configuration and data acquisition for slow cameras (Princetons, Andors, etc).

  Methods:
    configure             Updates the configuration values of the manager instance
    takeShots             Acquires camera images
    takeShotsInteractive  Interactive version of the takeShots method
    ascan                 Performs a 1D absolute scan aquiring image(s) at each scan point
    a2scan                Performs a 2D absolute scan aquiring image(s) at each scan point
    dscan                 Performs a 1D relative scan aquiring image(s) at each scan point

  All the configuration fields of this object described below are used as default values when calling methods in
  this class. All of these values can be overridden in the method calls.

  Fields:
    numImages:    The number of images to acquire from the camera.
    numShots:     The number of X-ray pulses to integrate over for each image taken.
    expDelay:     The number of extra seconds to add to the calculated exposure time for the camera. In general the
                  exposure time set for the camera is as follows (in seconds):

                  'exposureTime = max(1, openDelay)/120.0 + numShots / burstRate) + expDelay'

    postDelay:    The number of seconds to delay after playing the sequencer when acquiring images. DO NOT USE THIS!
                  This parameter is no longer necessary and was only kept for backwards compatibility. It was only
                  needed for ancient versions of the daq where the number of events acquired in a run could not be
                  reliably determined. In those cases it needed to be set to something larger than the readout time
                  of the camera.
    openDelay:    The number of delta beams to delay after the camera start acquistion event code before
                  starting the MCC burst or opening the pulse picker
    burstRate:    The rate to use for MCC bursts. Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
    simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or open X-ray shutter,
                  but all other aspects work as normal.
    shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In other words use
                  an X-ray shutter (generally the XIP pulse picker) instead of MCC burst mode for exposing
                  the camera.
  """
  def __init__(self, pvSeq, idSeq, eventCameraOpen, eventShutterOpenClose, eventDaqReadout, eventDaqSlowReadout, beamDbKey, simDbKey, readoutGrps, daq, daqcfg=None, shutterInit=None):
    """
    Constructor of the SlowCameraManager class.

    Args:
      pvSeq:                  The base PV name of the event sequencer to use.
      idSeq:                  The sequence id number of the event sequencer to use.
      eventCameraOpen:        The event code used for signaling the start acquisition of the slow
                              camera. This may either be used as a physical TTL output or a command
                              evr signal for software acquisition starts.
      eventShutterOpenClose:  The event code used for triggering the open/close of the X-ray
                              shutter. Only used when in shutterMode.
      eventDaqReadout:        The event code used for daq readout each of the X-ray shots in the
                              sequence. Also used as the daq readout event code when not using
                              readout groups.
      eventDaqSlowReadout:    The event code used for daq readout of the slow cameras when readout
                              groups are enabled.
      beamDbKey:              The configuration Db key to use for configuring the cameras.
      simDbKey:               The configuration Db key to use for configuring the cameras when in
                              simulation mode. It can be the same as the regular Db key.
      readoutGrps:            Boolean for using a separate readout group from the fase devices for
                              the slow cameras. Setting this to 'True' is recommended.
      daq:                    Reference to an instance of either the raw pydaq.Control class or
                              or the higher level blbase.Daq wrapper class. If none is passed it
                              will attempt to create one when needed.
      daqcfg                  Reference to an instance of a blbase.DaqConfig class with an already
                              allocated pycdb instance. If none is passed it will attempt to create
                              one when needed.
      shutterInit:            Reference to a function for initializing the X-ray shutter used for
                              shutterMode. Should take the number of shots to open the shutter for
                              as a parameter. Generally this will be the set_mode function of the
                              XIP pulsepicker class.
    """
    self._seqConfig = SeqConfig(pvSeq, idSeq, eventCameraOpen, eventShutterOpenClose, eventDaqReadout, eventDaqSlowReadout, beamDbKey, simDbKey, readoutGrps, shutterInit)
    self._daq = daq
    self._daqcfg = daqcfg
    self._interactive = SlowCameraInteractive(self._seqConfig, self._daq, self._daqcfg)
    self._motors = []
    # Traditional default settings for the old scripts
    self.numImages    = 1
    self.numShots     = 1
    self.expDelay     = 0
    self.postDelay    = 0
    self.openDelay    = 5
    self.burstRate    = 120.0
    self.simMode      = False
    if shutterInit is None:
      self.shutterMode = False
    else:
      self.shutterMode = True
    self._slowcamScan = None
    self._nScanShots  = 1
    self._nScanImages = 1
    self._nScanStep   = 0
    self._calibcontrols = []

  def __repr__(self):
    strval  = '%s:\n' % self.__class__.__name__
    strval += ' numImages:   %s\n' % self.numImages
    strval += ' numShots:    %s\n' % self.numShots
    strval += ' expDelay:    %s\n' % self.expDelay
    strval += ' postDelay:   %s\n' % self.postDelay
    strval += ' openDelay:   %s\n' % self.openDelay
    strval += ' burstRate:   %s\n' % self.burstRate
    strval += ' simMode:     %s\n' % self.simMode
    strval += ' shutterMode: %s\n' % self.shutterMode
    strval += ' SeqConfig:   %s\n' % self._seqConfig
    return strval
    
  def configure(self, numImages, numShots, expDelay, postDelay, openDelay, burstRate, simMode, shutterMode):
    """
    Updates all the configuration fields of this object. These configuration values are used as
    defaults when calling methods in this class. All of these values can be overridden
    directly in those method calls.

    Args:
      numImages:    The number of images to acquire from the camera.
      numShots:     The number of X-ray pulses to integrate over for each image taken.
      expDelay:     The number of extra seconds to add to the calculated exposure time for the camera. In general the
                    exposure time set for the camera is as follows (in seconds):

                    'exposureTime = max(1, openDelay)/120.0 + numShots / burstRate) + expDelay'

      postDelay:    The number of seconds to delay after playing the sequencer when acquiring images. DO NOT USE THIS!
                    This parameter is no longer necessary and was only kept for backwards compatibility. It was only
                    needed for ancient versions of the daq where the number of events acquired in a run could not be
                    reliably determined. In those cases it needed to be set to something larger than the readout time
                    of the camera.
      openDelay:    The number of delta beams to delay after the camera start acquistion event code before
                    starting the MCC burst or opening the pulse picker
      burstRate:    The rate to use for MCC bursts. Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
      simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or open X-ray shutter,
                    but all other aspects work as normal.
      shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In other words use
                    an X-ray shutter (generally the XIP pulse picker) instead of MCC burst mode for exposing
                    the camera.
    """
    self.numImages   = numImages
    self.numShots    = numShots
    self.expDelay    = expDelay
    self.postDelay   = postDelay
    self.openDelay   = openDelay
    self.burstRate   = burstRate
    self.simMode     = simMode
    self.shutterMode = shutterMode

  def _check_param(self, param, def_param):
    if param is None:
      return def_param
    else:
      return param
      
  def takeShotsInteractive(self, numShots=None, expDelay=None, postDelay=None, openDelay=None, burstRate=None, simMode=None, shutterMode=None):
    """
    Launches an interactive session for controlling camera acquisition.

    Once the interactive session has finished initializing the user is given a prompt that works as follows:
    --Enter a number + <Enter> to get more images, or just Hit <Enter> to end run and exit--

    In all other respects than controlling the number of images it functions identically to the 'takeShots' method.

    Args: (these are used to override the default configuration values in the slow camera manager)
      numShots:     The number of X-ray pulses to integrate over for each image taken.
      expDelay:     The number of extra seconds to add to the calculated exposure time for the camera. In general the
                    exposure time set for the camera is as follows (in seconds):

                    'exposureTime = max(1, openDelay)/120.0 + numShots / burstRate) + expDelay'

      postDelay:    The number of seconds to delay after playing the sequencer when acquiring images. DO NOT USE THIS!
                    This parameter is no longer necessary and was only kept for backwards compatibility. It was only
                    needed for ancient versions of the daq where the number of events acquired in a run could not be
                    reliably determined. In those cases it needed to be set to something larger than the readout time
                    of the camera.
      openDelay:    The number of delta beams to delay after the camera start acquistion event code before
                    starting the MCC burst or opening the pulse picker
      burstRate:    The rate to use for MCC bursts. Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
      simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or open X-ray shutter,
                    but all other aspects work as normal.
      shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In other words use
                    an X-ray shutter (generally the XIP pulse picker) instead of MCC burst mode for exposing
                    the camera.
    """
    return self._interactive.run(
      self._check_param(numShots, self.numShots),
      self._check_param(expDelay, self.expDelay),
      self._check_param(postDelay, self.postDelay),
      self._check_param(openDelay, self.openDelay),
      self._check_param(burstRate, self.burstRate),
      self._check_param(simMode, self.simMode),
      self._check_param(shutterMode, self.shutterMode),
    )

  def takeShots(self, numImages=None, numShots=None, expDelay=None, postDelay=None, openDelay=None, burstRate=None, simMode=None, shutterMode=None):
    """
    Acquires the requested number of images from the camera.

    This method sets up the camera configuration, event sequencer, DAQ, and pulsepicker (if needed),
    and then acquires the number of slow camera images requested. The images taken by this call will be
    one DAQ run.

    Args: (these are used to override the default configuration values in the slow camera manager)
      numImages:    The number of images to acquire from the camera.
      numShots:     The number of X-ray pulses to integrate over for each image taken.
      expDelay:     The number of extra seconds to add to the calculated exposure time for the camera. In general the
                    exposure time set for the camera is as follows (in seconds):

                    'exposureTime = max(1, openDelay)/120.0 + numShots / burstRate) + expDelay'

      postDelay:    The number of seconds to delay after playing the sequencer when acquiring images. DO NOT USE THIS!
                    This parameter is no longer necessary and was only kept for backwards compatibility. It was only
                    needed for ancient versions of the daq where the number of events acquired in a run could not be
                    reliably determined. In those cases it needed to be set to something larger than the readout time
                    of the camera.
      openDelay:    The number of delta beams to delay after the camera start acquistion event code before
                    starting the MCC burst or opening the pulse picker
      burstRate:    The rate to use for MCC bursts. Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
      simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or open X-ray shutter,
                    but all other aspects work as normal.
      shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In other words use
                    an X-ray shutter (generally the XIP pulse picker) instead of MCC burst mode for exposing
                    the camera.
    """
    slowcamDaq = SlowCamera(
      self._check_param(numShots, self.numShots),
      self._check_param(expDelay, self.expDelay),
      self._check_param(postDelay, self.postDelay),
      self._check_param(openDelay, self.openDelay),
      self._check_param(burstRate, self.burstRate),
      self._check_param(simMode, self.simMode),
      self._check_param(shutterMode, self.shutterMode),
      self._seqConfig,
      self._daq,
      self._daqcfg
    )
    if numImages is None:
      numImages = self.numImages
    iFail = slowcamDaq.init(controls=[],bDaqBegin=False)
    if iFail != 0:
      print "Failed to initalize the camera class!"
      return 1
    try:
      print("Will get %d images..." % numImages)
      slowcamDaq.beginCycle([])
      slowcamDaq.getMoreImages(numImages)
      slowcamDaq.endCycle()
    except:
      print "\n!!! Take shots exits abnormally (may be interrupted by user)"
      print "ERROR:",sys.exc_info()[0]
      return 1
    finally:
      daq = slowcamDaq.daq
      print "# (If Record Run is ON) Experiment %d Run %d (%d images)" % (daq.experiment(),daq.runnumber(), slowcamDaq.numTotalImage())
      slowcamDaq.deinit()

    return 0

  def _get_controls(self):
    controls=[]
    for m in self._motors:
      controls.append((m.name,m.wm()))
    return controls

  def _pre_scan(self, scan):
    print "Configuring Slow Camera..."
    iFail = self._slowcamScan.init(controls=self._calibcontrols,bDaqBegin=False)
    sys.stdout.flush()
    if iFail != 0:
      raise Exception("Failed to initalize the camera!")

  def _post_scan(self, scan):
    daq = self._slowcamScan.daq
    print "# (If Record Run is ON) Experiment %d Run %d (%d images)" % (daq.experiment(),daq.runnumber(), self._slowcamScan.numTotalImage())
    self._slowcamScan.deinit()

  def _post_move(self, scan):
    position = "step: %5d \t position: " % self._nScanStep; self._nScanStep += 1
    for m in self._motors:
      position += "\t%10.4f" % (m.wm())
    print position

    print("Will get %d images..." % self._nScanImages)
    sys.stdout.flush()
    controls=self._get_controls()
    #controls = []
    self._slowcamScan.beginCycle(controls)
    self._slowcamScan.getMoreImages(self._nScanImages)
    self._slowcamScan.endCycle()

  def ascan(self, motor, pos1, pos2, nIntervals, numShots=1, numImages=1, returnAfter=True, burstRate=None, simMode=None, shutterMode=None):
    """
    Runs a 1d absolute scan acquiring images at each point in the scan.

    This routine runs a 1-dimensional scan of a motor from pos1 to pos2 in nIntervals
    steps. The delta between points is (pos2 - pos1) / nIntervals. The actual number
    of points in the scan will be nIntervals + 1 since both pos1 and pos2 are used as
    points. At each point in the scan the number of images specified by numImages is
    acquired from the camera. By default the motor will be moved back to it's position
    at the start of the scan.

    Examples:
        ascan(fake_motor, 0.0, 10.0, 10): This will do eleven scan points with motor
            positions for fake motor of: 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
            9.0, 10.0. It will acquire one image from the camera at each point since
            that is the default value of the numImages argument.

        ascan([fake_motor_1, fake_motor_2], 0.0, 10.0, 10): This will do eleven scan
            points moving both fake_motor_1 and fake_motor_2 at each scan point. In
            this case since pos1 and pos2 are not lists both motors will be scanned
            through the set of points 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
            9.0, 10.0.

        ascan([fake_motor_1, fake_motor_2], 0.0, [5.0, 10.0], 10): his will do eleven
            scan points moving both fake_motor_1 and fake_motor_2 at each scan point.
            In this case because pos2 is a list fake_motor_1 will be scanned through
            the set of points 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
            and fake_motor_2 will be scanned through the points 0.0, 1.0, 2.0, 3.0,
            4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0.

    Args:
      motor:        The motor(s) to move for each scan point. May be a single motor
                    object or a sequence (list, tuple, etc.) of motor objects.
      pos1:         The initial starting position(s) for the motor(s) for the scan.
                    Can be a single value or list of values when using more than
                    one motor.
      pos2:         The final position(s) for the motor(s) for the scan. Can be
                    a single value or list of values when using more than one
                    motor.
      nIntervals:   The number of intervals in the scan. The delta between points
                    in the scan is (pos2 - pos1) / nIntervals. The actual number
                    of points in the scan will be nIntervals + 1.
      numShots:     The number of X-ray pulses to integrate over for each image taken.
      numImages:    The number of images to acquire from the camera and each scan point.
      returnAfter:  A boolean flag for indicating whether the motor should be returned
                    to it's initial, pre-scan position at the completion of the scan. If it
                    is set to false the motor(s) will be left at position specified by pos2.
      burstRate:    The rate to use for MCC bursts. Defaults to the value set in the slow
                    camera manager config if no value is passed.
                    Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
      simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or
                    open X-ray shutter, but all other aspects work as normal. Defaults to
                    the value set in the slow camera manager config if no value is passed.
      shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In
                    other words use an X-ray shutter (generally the XIP pulse picker)
                    instead of MCC burst mode for exposing the camera. Defaults to
                    the value set in the slow camera manager config if no value is passed.
    """
    retVal = 0
    print "Setting up scan..."
    try:
      self._calibcontrols=[('motor1_pos1',pos1),
                     ('motor1_pos2',pos2),
                     ('motor1_nIntervals',nIntervals),
                     ('nshots',numShots),
                     ('nimages',numImages)
                     ]
      self._nScanShots  = numShots
      self._nScanImages = numImages
      self._nScanStep   = 0
      if burstRate is None:
        self._scanBurst = self.burstRate
      else:
        self._scanBurst = burstRate
      if simMode is None:
        self._scanSim = self.simMode
      else:
        self._scanSim = simMode
      if shutterMode is None:
        self._scanShutter = self.shutterMode
      else:
        self._scanShutter = shutterMode
      self._motors = [motor]
      self._calibcontrols += self._get_controls()
      self._slowcamScan = SlowCamera(numShots, self.expDelay, self.postDelay, self.openDelay, self._scanBurst, self._scanSim, self._scanShutter, self._seqConfig, self._daq, self._daqcfg)
      scan = AScan(motor, pos1, pos2, nIntervals, returnAfter)
      scan.set_pre_scan_hook(self._pre_scan)
      scan.set_post_scan_hook(self._post_scan)
      scan.set_post_move_hook(self._post_move)
      print "Starting scan..."
      scan.go()
    finally:
      pass

  def dscan(self, motor, d1, d2, nIntervals, numShots=1, numImages=1, returnAfter=True, burstRate=None, simMode=None, shutterMode=None):
    """
    Runs a 1d relative scan acquiring images at each point in the scan.

    This routine runs a 1-dimensional scan of a motor from pos1 = d1 + p0 to pos2 = d2 + p0
    in nIntervals steps were p0 is the current position of the motor. The delta between
    points is (pos2 - pos1) / nIntervals. The actual number of points in the scan will be
    nIntervals + 1 since both pos1 and pos2 are used as points. At each point in the scan
    the number of images specified by numImages is acquired from the camera. By default
    the motor will be moved back to it's position at the start of the scan. This function
    works identically to ascan except the beginning and ending scan points are specified
    relative to the current position of the motor instead of absolute motor coordinates.

    Example:
        dscan(fake_motor, -5.0, 5.0, 10): If the motor is at a current position of -3.0.
            This will do eleven scan points with motor positions for fake motor of:
            -8.0, -7.0, -6.0, -5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0. It will acquire
            one image from the camera at each point since that is the default value of the
            numImages argument. Since returnAfter defaults to True the motor will be
            returned to a position of -3.0 on completion of the scan.

    Args:
      motor:        The motor(s) to move for each scan point. May be a single motor
                    object or a sequence (list, tuple, etc.) of motor objects.
      d1:           The initial starting position(s) for the motor(s) for the scan.
                    Can be a single value or list of values when using more than
                    one motor.
      d2:           The final position(s) for the motor(s) for the scan. Can be
                    a single value or list of values when using more than one
                    motor.
      nIntervals:   The number of intervals in the scan. The delta between points
                    in the scan is (pos2 - pos1) / nIntervals. The actual number
                    of points in the scan will be nIntervals + 1.
      numShots:     The number of X-ray pulses to integrate over for each image taken.
      numImages:    The number of images to acquire from the camera and each scan point.
      returnAfter:  A boolean flag for indicating whether the motor should be returned
                    to it's initial, pre-scan position at the completion of the scan. If it
                    is set to false the motor(s) will be left at position specified by pos2.
      burstRate:    The rate to use for MCC bursts. Defaults to the value set in the slow
                    camera manager config if no value is passed.
                    Must be a valid beamrate e.g. 120, 60, 30, ... , 0.5.
      simMode:      Boolean flag for enabling simulation mode. Do not call MCC bursts or
                    open X-ray shutter, but all other aspects work as normal. Defaults to
                    the value set in the slow camera manager config if no value is passed.
      shutterMode:  Boolean flag for enabling shuttered mode as opposed to burst mode. In
                    other words use an X-ray shutter (generally the XIP pulse picker)
                    instead of MCC burst mode for exposing the camera. Defaults to
                    the value set in the slow camera manager config if no value is passed.
    """
    ascan(motor,motor.wm()+d1,motor.wm()+d2,nIntervals,numShots,numImages,returnAfter,burstRate,simMode,shutterMode)

  def a2scan(self, motor1, motor1_pos1, motor1_pos2, motor1_nIntervals, motor2, motor2_pos1, motor2_pos2, motor2_nIntervals, numShots=1, numImages=1, returnAfter=True, burstRate=None, simMode=None, shutterMode=None):
    retVal = 0
    print "Setting up scan..."
    try:
      calibcontrols=[('motor1_pos1',motor1_pos1),
                     ('motor1_pos2',motor1_pos2),
                     ('motor1_nIntervals',motor1_nIntervals),
                     ('motor2_pos1',motor1_pos1),
                     ('motor2_pos2',motor2_pos2),
                     ('motor2_nIntervals',motor2_nIntervals),
                     ('nshots',numShots),
                     ('nimages',numImages)
                    ]
      self._nScanShots  = numShots
      self._nScanImages = numImages
      self._nScanStep   = 0
      if burstRate is None:
        self._scanBurst = self.burstRate
      else:
        self._scanBurst = burstRate
      if simMode is None:
        self._scanSim = self.simMode
      else:
        self._scanSim = simMode
      if shutterMode is None:
        self._scanShutter = self.shutterMode
      else:
        self._scanShutter = shutterMode
      self._motors = [motor1, motor2]
      self._calibcontrols += self._get_controls()
      self._slowcamScan = SlowCamera(numShots, self.expDelay, self.postDelay, self.openDelay, self._scanBurst, self._scanSim, self._scanShutter, self._seqConfig, self._daq, self._daqcfg)
      scan = A2Scan(motor1, motor1_pos1, motor1_pos2, motor1_nIntervals, motor2, motor2_pos1, motor2_pos2, motor2_nIntervals, returnAfter)
      scan.set_pre_scan_hook(self._pre_scan)
      scan.set_post_scan_hook(self._post_scan)
      scan.set_post_move_hook(self._post_move)
      print "Starting scan..."
      scan.go()
    finally:
      pass

def showUsage():
  sFnCmd = os.path.basename( sys.argv[0] )
  print(
    "Usage: %s [-h | --help] [-m|--mshot <NumShots>] [-e|--expdelay <Delay>] [-p|--post <postDealy>]\n"
    "    [-o|--opendelay <Tick>] [-r|--rate <rate>] [-s|--shutter] [--hutch <Hutch>]" % sFnCmd )
  print( "    -h | --help                   Show usage information" )
  print( "    -m | --mshot     <NumShots>   Run multiple shot integration of <NumShots>. Default: 1" )
  print( "    -e | --expdelay  <Delay>      Set exposure time delay to <Delay> second. Default: 0" )
  print( "    -p | --post      <PostDelay>  Set post delay to <Delay> second. Default: 0" )
  print( "    -o | --opendelay <Tick>       Set camera open delay to <Tick>/120 seconds. Default: 5")
  print( "    -r | --rate      <Rate>       Set burst rate to <rate>. Default: use Beam Rate" )
  print( "    -s | --shutter                Run in shutter mode. No Mcc Burst is called.")
  print( "         --sim                    Run in simulation mode: No Mcc burst, and no shutter.")
  print( "         --hutch     <Hutch>      Set the hutch configuration to use. Default: %s"%blutil.guessBeamline())
  print( " ver 1.10")

def main():
  (llsOptions, lsRemainder) = getopt.getopt(sys.argv[1:], \
      'hm:e:r:p:o:s', \
      ['help', 'mshot=', 'expdelay=', 'rate=', 'post=', 'opendelay=', 'shutter', 'sim','hutch='] )

  config = {
    'sxr' : SeqConfig("SXR:ECS:IOC:01", 2, 80, 75, 81, 82, 'PRINCETON_BURST', 'PRINCETON_SIM', True),
    'xpp' : SeqConfig("XPP:ECS:IOC:01", 3, 93, 94, 95, 97, 'PRINCETON', 'PRINCETON', True),
    'xcs' : SeqConfig("XCS:ECS:IOC:01", 4, 83, 84, 85, 87, 'PRINCETON_BURST', 'PRINCETON_SIM', True),
  }

  numShots   = 1
  expDelay   = 0
  postDelay  = 0
  openDelay  = 5

  burstRate   = 120.0
  simMode     = False
  shutterMode = False
  hutch       = None
  for (sOpt, sArg) in llsOptions:
    if sOpt in ('-h', '--help' ):
      showUsage()
      return 1
    elif sOpt in ('-m', '--mshot'):
      numShots   = int(sArg)
    elif sOpt in ('-e', '--expdelay'):
      expDelay  = float(sArg)
    elif sOpt in ('-p', '--post'):
      postDelay = float(sArg)
    elif sOpt in ('-o', '--opendelay'):
      openDelay = int(sArg)
    elif sOpt in ('-r', '--rate'):
      burstRate   = float(sArg)
    elif sOpt == '-s' or sOpt == '--shutter':
      shutterMode = True
    elif sOpt == '--sim':
      simMode     = True
    elif sOpt == '--hutch':
      hutch = sArg

  print "Command line: NumShot %d ExpDelay %g PostDelay %g OpenDelay %d Rate %g SimMode %s Shutter %s" % \
    (numShots, expDelay, postDelay, openDelay, burstRate, simMode, shutterMode)
  try:
    if hutch is None:
      hutch = blutil.guessBeamline()
    else:
      hutch = hutch.lower()
    if hutch not in config:
      raise ValueError("Invalid hutch selection: %s"%hutch)     
    SlowCameraInteractive(config[hutch]).run(numShots, expDelay, postDelay, openDelay, burstRate, simMode, shutterMode)
  except:
    traceback.print_exc(file=sys.stdout)
    print "ERROR:",sys.exc_info()[0]
  return

if __name__ == '__main__':
  status = main()
  sys.exit(status)
