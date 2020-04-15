import os
import time
import math
import threading

from psp import Pv 
from blbase.motor import Motor
from blbase.virtualmotor import VirtualMotor
#from blutil import config, estr, printnow
from blutil import printnow
from blbase.daq_config_device import Dcfg

from pswww import pypsElog
import beamline as env

import numpy as np
import importlib
importlib.sys.path.append('/reg/neh/home/koglin/package/trunk/pscontrol')
from psmessage import Message
from blbase import controlevr

expname = os.path.basename(__file__).split(".")[0]

class Experiment(object):
    """CFEL fixed target "row runner" experiment 
       
       copied from last cxi roadrunner experiment /reg/g/pcds/pyps/mfx/dev/mfx/experiments/mfxx28815.py
       started from initial experiment in xpp /reg/g/pcds/pyps/xpp/dev/xpp/experiments/xpph9015.py
    """
    instrument = expname[0:3]
    expname = expname[3:]
    feedback_nobeam = 0.0
    feedback_beam = 5.0
    # 1V = 3276
    ttl_high = -10000
    ttl_low = -200
    _base_freq = 120.0

#    _pp_conf = 0
    elog = pypsElog.pypsElog()
    motor_evr = controlevr.ControlEVR("CXI:R52:EVR:01","CXI").t1
#    motor_evr = controlevr.ControlEVR("CXI:REC:EVR:04","CXI").t1
    # Use same eventCode as MFX
    motor_ec = 187

    _pvs = {'ANGLE'  : {'pv': 'CXI:USR:ANGLE',  'type': float,
                        'desc': 'Sample Angle', 'units': 'deg'},
            'CHIP'   : {'pv': 'CXI:USR:NAME',   'type': str, 
                        'desc': 'Sample Name'},
            'HORIZONTALPITCH'  : {'pv': 'CXI:USR:HORIZONTALPITCH',  'type': float,
                        'desc': 'HORIZONTAL Hole Pitch', 'units': 'um'},
            'VERTICALPITCH'  : {'pv': 'CXI:USR:VERTICALPITCH',  'type': float,
                        'desc': 'Vertical Hole Pitch', 'units': 'um'},
            'TYPE'   : {'pv': 'CXI:USR:TYPE',   'type': str,
                        'desc': 'Sample Type'},
            'FREQ'   : {'pv': 'CXI:USR:FREQ',   'type': int, 
                        'desc': 'XFEL Rate', 'units': 'Hz',
                        'in_valid': [120, 30, 20, 10, 5, 1]},
            'ROW'    : {'pv': 'CXI:USR:ROW',    'type': int,
                        'desc': 'Sample Row'},
            'ACC'    : {'pv': 'CXI:USR:ACC',    'type': int,
                        'desc': 'Accel Pulses'},
            'PATT'   : {'pv': 'CXI:USR:PATT',   'type': float,
                        'desc': 'Sample Pattern'},
            'COMM'   : {'pv': 'CXI:USR:COMM',   'type': str,
                        'desc': 'Sample Comment'},
            'CELLS'  : {'pv': 'CXI:USR:CELLS',  'type': int,
                        'desc': 'Cells per Holder'},
            'WINDOWS': {'pv': 'CXI:USR:WINDOWS','type': int,
                        'desc': 'No. of Holders'},
            'GAP'    : {'pv': 'CXI:USR:GAP',    'type': int,
                        'desc': 'Gap btw. Holders'},
            'STOP'   : {'pv': 'CXI:USR:STOP',    'type': int,
                        'desc': 'STOP EVERYTHING'},
            'STARTROW': {'pv': 'CXI:USR:STARTROW',    'type': int,
                        'desc': 'START ROW'},
            'USELASER': {'pv': 'CXI:USR:USELASER',    'type': int,
                        'desc': 'uselaser'},
            'laser_enabled': {'pv': 'CXI:R52:EVR:01:TRIG1:TPOL', 'type': int}, 
            'control_sig': {'pv': 'CXI:SC2:AIO:01:ANALOGOUT', 
                        'write': False},
            'gasdet_sig': {'pv': 'GDET:FEE1:241:ENRC',
                        'write': False},
            'um6_shutter_cmd': {'pv': 'HXX:UM6:STP:01:CMD', 'type': int},
            'um6_shutter_opn': {'pv': 'HXX:UM6:STP:01:OPEN', 'type': int},
            'um6_shutter_cls': {'pv': 'HXX:UM6:STP:01:CLOSE', 'type': int},
           }
        
    def __init__(self):

        self._daq = env.daq
        for pv,item in self._pvs.items():
            print 'Adding ',pv, item
            item['Pv'] = Pv.Pv(item['pv'])
        
        self._daq = env.daq
        self.hutch=expname[0:3]
        self.aliases=['BEAM']

        #Add monitor callback for AI
        print 'adding analog input'
        self.analog = Pv.Pv('CXI:SC2:AIO:01:RAW:ANALOGIN')
        print 'add callback' 
        self.analog.add_monitor_callback(self.make_ready)
        print 'add threading'
        self.ready_for_row = threading.Event()
        self.latch = False
        self.event_timeout = 0.05 # timeout in seconds on event wait
        #self._init_stop_callback()

    # Need to add this PV in pvNotepad or some other host sioc.
    def _init_stop_callback(self):
        #Add monitor callback for Stop
        self.stop_pv = Pv.Pv('CXI:USR:STOP')
        self.stop_pv.add_monitor_callback(self.stop_beam)
        self.stop_pv.monitor_start()

#    def set_sequencer_single(self, daq_code=187, beam_rate=30, picker=True):
#        """
#        Simple set sequencer for cxi daq readout
#        """
#        #self.clear_sequencer()
#        env.event.setSyncMarker(beam_rate)
#        env.event.stop()
#        if picker:
#            env.pp.prepare_FlipFlop(1, readoutCode=daq_code, prePP=2)
#        else:
#            env.event.setnsteps(1)
#            seqstep = 0
#            env.event.setstep(seqstep, daq_code, 0,fiducial=0,comment='Daq Readout');seqstep+=1
#            env.event.update()
#            time.sleep(2)
#
    @property
    def _pp(self):
        return env.pp

    def __getattr__(self, attr):
        if attr in self._pvs:
            return self._pvs[attr]['Pv'].get()

    def __setattr__(self, attr, value):
        if attr in self._pvs:
            if self._pvs[attr].get('in_valid'):
                if value not in self._pvs[attr].get('in_valid'):
                    print 'Invalid input'
                    return None

            return self._pvs[attr]['Pv'].put(value)
        else:
            self.__dict__[attr] = value

    def __repr__(self):
        print '--------------------------------'
        self.sample_info().show()
        self.step_info().show()
        return '<{:}{:}>'.format(self.instrument,self.expname)

    def __dir__(self):
        all_attrs = set(self._pvs.keys() +
                        self.__dict__.keys() + dir(Experiment))

        return list(sorted(all_attrs))
 
    def stop_beam(self,result):
        """
        Callback function to stop the beam
        """
        if self.stop_pv.value != 0:
            printnow('Received stop signal')
            self._pp.close()
            #env.event.stop()
            #self._pp.close() 

    def free_run(self, nevents=432000, eventCode=None, daq=True,
            start=False, beam_rate=30, picker=True, prePP=3, test=False):
        """
        Free run for nevents
        """
        if test:
            picker_ec = 201
        else:
            picker_ec = self._pp._codes['pp']

        motor_ec = self.motor_ec
        readout_ec = self._pp._codes['daq']
        drop_ec = self._pp._codes['drop']
        
        seqstep=0
        if not eventCode:
            eventCode = self.motor_ec

        env.event.setSyncMarker(beam_rate)
        env.event.stop()
        if picker:
            env.event.setstep(seqstep, env.pp._codes['pp'], prePP,fiducial=0,comment='PulsePicker');seqstep+=1
            env.event.setstep(seqstep, env.pp._codes['drop'], 0,fiducial=0,comment='OffEvent');seqstep+=1
            env.event.setstep(seqstep, eventCode, 1,fiducial=0,comment='DaqReadout');seqstep+=1
        else:
            env.pp.close()
            env.event.setstep(seqstep, eventCode, 1,fiducial=0,comment='DaqReadout');seqstep+=1
        
        env.event.setnsteps(seqstep)
        for i in range(seqstep-20):
            env.event.setstep(seqstep, 0, 0,fiducial=0,comment=' ');seqstep+=1
        env.event.update()
        printnow("Done with sequence\n")
        env.event.modeForever()
        if start:
            env.event.start()
        if daq:
            env.daq.connect()
            env.daq.begin(nevents)

    def stop_freerun(self, daq=True):
        env.event.stop()
        if daq:
            env.daq.endrun()

    def make_ready(self,result):
        """
        Callback function to check a change in the Analog channel
        """
        if self.analog.value < self.ttl_high and not self.latch:
            printnow('Received TTL Pulse, setting ready flag\n')
            self.latch = True
            self.ready_for_row.set()
        elif self.analog.value > self.ttl_low:
            self.latch = False
 
#    def auto_run(self):
#        pv = Pv.Pv('CXI:USR:START')
#        pv.monitor_start()
#        while True:
#            if pv.value is True:
#                self.start_run()
#            else:
#                time.sleep(1)


    def configure_sequencer(self,test=False,readOnMotor=True, addDrop=False):
        """
        Configure the sequencer based on the current set of USER PVS
        
        Epics pv inputs that define event sequence:
        - nstart=CXI:USR:ACC:       the number of sync pulses to send before starting xray pulses.
        - ncells=CXI:USR:CELLS:     the number of cells to shoot in a row of the sample holder.
        - freq=CXI:USR:FREQ:        the frequency used for both motor sync triggers and the xray pulses (default: 120 Hz).
        - ngap=CXI:USR:GAP:         gap between windows
        - nwindows=CXI:USR:WINDOWS  number of windows
        """
        nstart=self.ACC
        ncells=self.CELLS
        nwindows=self.WINDOWS
        ngap=self.GAP
        freq=self.FREQ
        sample_name=self.CHIP
        runstr = None
        # Sequencer set to use burst delay off of next shot
        self._pp._burstdelay = 0.0008
        self._pp._flipflopdelay = 0.0008
        if test:
            picker_ec = 201
        else:
            picker_ec = self._pp._codes['pp']

        self.STOP = 0
       
        motor_ec = self.motor_ec
        readout_ec = self._pp._codes['daq']
        drop_ec = self._pp._codes['drop']

        latch = False
        # istep is the daq run 'calibration' step    
        istep = 0
        env.event.modeOnce()
        seqstep = 0
        motsync_com = 'MotorSync'
        readout_com = 'Readout'
        pp_com = 'PulsePicker'
        drop_com = 'DroppedShot'
        if self._base_freq % freq != 0:
            printnow("Warning: %.1f is not an allowed frequency - choosing closest avaiable!"%freq)
        pulse_step = int(math.ceil(self._base_freq/freq))
        printnow("Configuring sequencer for rows with %d cells at pulse frequency of %.1f Hz ..."%(ncells, self._base_freq/pulse_step))
        printnow('***********************************\n')
        printnow(self.sample_info())
        if pulse_step == 1:
            ## set pulse picker to burst mode
            #if Pv.get(self._pp._PVname('SE')) != 3:
            print 'Setting PulsePicker to Burst mode'
            #Pv.put(self._pp._PVname('RUN_BURSTMODE'),1)
            self._pp.burst()

            # adding starting pulses before pulse pickers starts to open
            for index in range(nstart):
                env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                if addDrop:
                    env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1
            # Repeat for nwindows:
            for iwindow in range(nwindows):
                # open pulse picker
                env.event.setstep(seqstep, picker_ec, 0,fiducial=0,comment=pp_com);seqstep+=1
                # add all but the last xray shot
                for index in range(ncells):
                    # close pulsepicker and read last shot in window
                    if index == ncells-1:
                        env.event.setstep(seqstep, picker_ec, 0,fiducial=0,comment=pp_com);seqstep+=1
                    env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                    if not readOnMotor:
                        env.event.setstep(seqstep, readout_ec, 0,fiducial=0,comment=readout_com);seqstep+=1
                
                # Skip ngap pulses for each window
                for igap in range(ngap):
                    env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                    if addDrop:
                        env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1

            # Provide Motor Sync pulses for deacceleration
            for index in range(nstart-ngap):
                env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                if addDrop:
                    env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1
        
        elif pulse_step >= 4:
            # set pulse picker to flip flop mode
            if Pv.get(self._pp._PVname('SE')) != 2:
                print 'Setting PulsePicker to FlipFlop mode'
                #Pv.put(self._pp._PVname('RUN_FLIPFLOP'),1)
                self._pp.flipflop()
            # adding starting MotorSync pulses before pulse pickers starts to open
            for index in range(nstart):
                env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                if addDrop:
                    env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1
            # start ncell number of flip-flops of the pulse picker
            pp_open_delay = 1 
            pp_ff_delay = pulse_step - pp_open_delay
            for iwindow in range(nwindows):
                for index in range(ncells):
                    env.event.setstep(seqstep, picker_ec, pp_ff_delay,fiducial=0,comment=pp_com);seqstep+=1
                    if not readOnMotor:
                        env.event.setstep(seqstep, readout_ec, pp_open_delay,fiducial=0,comment=readout_com);seqstep+=1
                    else:
                        env.event.setstep(seqstep, drop_ec, pp_open_delay,fiducial=0,comment=drop_com);seqstep+=1
                    env.event.setstep(seqstep, motor_ec, 0,fiducial=0,comment=motsync_com);seqstep+=1
                # Skip ngap pulses for each window
                for igap in range(ngap):
                    env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                    if addDrop:
                        env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1

            # Add additional deceleration pulses for MotorSync
            for index in range(nstart):
                env.event.setstep(seqstep, motor_ec, pulse_step,fiducial=0,comment=motsync_com);seqstep+=1
                if addDrop:
                    env.event.setstep(seqstep, drop_ec, 0,fiducial=0,comment=drop_com);seqstep+=1
        
        else:
            printnow("\nA frequency choice of %.2f Hz is not allowed in this mode! - Aborting...\n"%freq)
            return
        
        # finalize sequence
        env.event.setnsteps(seqstep)
        env.event.update()
        printnow("Done with sequence\n")


    def start_run(self, 
            use_daq=False, use_steps=True, record=None, test=False, post=True, 
            gasdet_min=-1., readOnMotor=True, addDrop=True, configure=True,
            safe=False, **kwargs):
        """
        Runs the sequence for a row of samples in a loop until aborted.

        Each interation of the loop it waits to receive a rising edge signal from the motion controller 
        before starting to play the sequence. Once the sequence is started it sends a continous set of sync 
        triggers to the motion controller at the desired frequency.

        - gasdet_min:  minimum gas detector value (GDET:FEE1:241:ENRC) to start a row [mJ] (default: -1)
        - use_daq: this controls whether the script will start running the daq and take a calib cycle for each row (default: False).
        - use_steps:  u
        - test:    mode where pulse picker is not used
        - record:  this controls the recording state of the daq (only meaningful if 'use_daq' is set to True).
            * True:  force recording of the run.
            * False: force off recording of the run.
            * None:  use the option selected in the daq gui (default).
        
        - configure: Configure the Sequencer with the current set of PVS
        
        """
        ####
        safe=False
        ####
        nstart=self.ACC
        ncells=self.CELLS
        nwindows=self.WINDOWS
        ngap=self.GAP
        freq=self.FREQ
        sample_name=self.CHIP
        runstr = None
        istep = 0
        self.STOP = 0
        if configure:
            self.configure_sequencer()

        self.analog.monitor_start()
        
        try:
            # configure daq if being used
            if use_daq:
                env.daq.record = record
                calibcontrols=[
                                ('nstart', nstart),
                                ('ncells', ncells),
                                ('nwindows', nwindows),
                                ('freq', freq),
                                ('angle', self.ANGLE),
                                ('row', self.ROW),
                                ('horizontalpitch', self.HORIZONTALPITCH),
                                ('verticalpitch', self.VERTICALPITCH),
                                ('pattern', self.PATT),
                              ]
                env.daq.configure(controls=calibcontrols,events=0)
                if not use_steps:
                    env.daq.begin(events=0,controls=calibcontrols)
                    run_num = env.daq.runnumber()

            if test:
                runstr = 'Test No Beam'
            else:
                runstr = 'Run {:}'.format(env.daq.runnumber())
        
            printnow("if desired setup DAQ & wrote sample_name %s to PV; now waiting for ready signal\n"%sample_name)
            message = self.sample_info()
            
            if safe:
                printnow("Opening the UM6 shutter...")
                self.um6_shutter_cmd = 1
                while self.um6_shutter_opn != 1:
                    time.sleep(0.01)
                printnow("done\n")

            #Start new row, ignore past input triggers
            self.ready_for_row.clear()
            printnow('Ready to run')
            Message('-------------------',append=True)
    
            self.STARTROW = 0
            time.sleep(0.2)
            while self.STOP == 0:
                
                # Now using epics CXI:USR:STARTROW instead of analog AI
                if self.STARTROW == 1:
                    try:
                        print "Pontus debug: USE LASER STATUS", self.USELASER
                        if self.USELASER:
                            self.laser_enabled=1
                        else:
                            self.laser_enabled=0

                    except:
                        print "Pontus fucked up"
                    self.STARTROW = 0
                    while self.gasdet_sig < gasdet_min:
                        time.sleep(1.)
                        printnow("Low beam = {:} mJ -- Waiting for beam to return ...\n".format(self.gasdet_sig))
                        Message("Low beam = {:} mJ -- Waiting for beam to return ...\n".format(self.gasdet_sig), append=True)

                    start_time = time.time()
                    if use_daq and use_steps:
                        calibcontrols=[
                                        ('nstart', nstart),
                                        ('ncells', ncells),
                                        ('nwindows', nwindows),
                                        ('freq', freq),
                                        ('angle', self.ANGLE),
                                        ('row', self.ROW),
                                        ('horizontalpitch', self.HORIZONTALPITCH),
                                        ('verticalpitch', self.VERTICALPITCH),
                                        ('pattern', self.PATT),
                                      ]
                        nEventsRecord = ncells*nwindows
                        if readOnMotor:
                            nEventsRecord = nstart+ncells*nwindows+(nwindows-1)*ngap
                        env.daq.begin(events=nEventsRecord,controls=calibcontrols)


                    #What is this / Why is this here                    
                    if (time.time()-start_time) < 0.2:
                        time.sleep(0.2-(time.time()-start_time))

                    if use_daq and use_steps:
                        run_num = env.daq.runnumber()
                        runstr = 'Run {:}'.format(run_num)
                    
                    try:
                        laser_state = 'Laser {:}'.format({0:'Off',1:'On'}.get(self.laser_enabled,'Unknown'))
                    except:
                        laser_state = 'Laser Unknown'

                    print laser_state
                    print runstr
                    self.istep = istep
                    self.runstr = runstr
                    printnow("Starting {:} Step {:}: {:} Row {:}, {:} deg angle ...\n".format(runstr, \
                                istep, self.CHIP, self.ROW, self.ANGLE))
                    step_message = "Step {:}: {:} Row {:}, {:} deg angle, {:}".format(istep, \
                                self.CHIP, self.ROW, self.ANGLE, laser_state)
                    
                    #Clear ready flag
                    self.ready_for_row.clear()
                    
                    env.event.start()
                    if use_daq and use_steps:
                        printnow('Waiting for DAQ end calib cycle')
                        env.daq.wait()
                        printnow('... done\n')

                    printnow('Waiting for Event Sequencer')
                    env.event.wait()
                    self.laser_enabled=0
                    printnow('... done\n')
                    stop_time = time.time()
                    printnow("   ... Completed in %.2f s\n"%(stop_time-start_time))
                    Message("{:} -- Completed in {:8.3f} s".format(step_message,stop_time-start_time), append=True)
                    istep += 1
                
                #Do we really need this sleep?    
                time.sleep(0.001)
                        
            printnow("Received STOP signal!\n")

        except KeyboardInterrupt:
            printnow("\nStopping row runner...")
            # abort sequencer
            env.event.stop()
            self._pp.close()
        
        finally:
            #self.seq_state = False

            # clear STOP flag
            self.STOP = 0
            self.analog.monitor_stop()
            
            if safe:
                printnow("Closing the UM6 shutter...")
                self.um6_shutter_cmd = 0
                while self.um6_shutter_cls != 1:
                    time.sleep(0.01)
                printnow("done\n")

            if use_daq:
                # revert daq record setting to gui control and disconnect
                #env.daq.wait()
                env.daq.stop()
                if runstr and post:
                    Message('{:}: {:} rows'.format(runstr,istep), append=True)
                    message = self.sample_info(append=True)
                    if record:
                        message.post(run_num=run_num)

                env.daq.record = None
                env.daq.disconnect()

    def sample_info(self, **kwargs):
        message = Message(quiet=True, **kwargs)
        for attr in ['COMM', 'CHIP', 'TYPE', 'FREQ', 'HORIZONTALPITCH', 'VERTICALPITCH',
                     'PATT', 'ACC', 'CELLS', 'WINDOWS', 'GAP']:
            item = self._pvs.get(attr)
            message('{:18}: {:8} {:6} (pv={:})'.format(item.get('desc'), getattr(self, attr), 
                item.get('units',''), item.get('pv')))

        return message        

    def step_info(self, **kwargs):
        message = Message(quiet=True, **kwargs)
        for attr in ['ROW', 'ANGLE']:
            item = self._pvs.get(attr)
            message('{:18}: {:8} {:6} (pv={:})'.format(item.get('desc'), getattr(self, attr), 
                item.get('units',''), item.get('pv')))
        
        return message

