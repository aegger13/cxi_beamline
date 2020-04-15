import os
import time
import beamline as env
import psp.Pv as Pv
from blbase.motor import Motor
from blbase.virtualmotor import VirtualMotor
from blbase.rowland import Rowland
from pswww import pypsElog

expname = os.path.basename(__file__).split(".")[0]

class Experiment(object):
    def __init__(self):
        self.expname = expname[3:]
        self.elog = pypsElog.pypsElog()

        self.laser = Laser()

        self.delay = VirtualMotor('delay', self.laser.set_delay, self.laser.get_delay)

    def scan_delay(self, start=-1, end=60, steps=305, events=120, 
            daq=True, record=True, config=True, set_sequencer=True, 
            post=None, quiet=False, comment=None, ascan=True, **kwargs):
        """
        Make a daq run.
        
        Parameters
        ----------
        start : flt
            Start time in ns
        end : flt
            End time in ns
        steps : int
            Number of steps (number of points = steps+1)
        events : int
            Number of events per step (recorded in calib cycles)
        ascan : bool
            Use hutchpython ascan method [default = True]
            Automatically sets epics PVs to describe scan for use in 
            Run Tables / User run summary table
        comment : str
            Comment to be posted in elog with scan info.
        post : bool
            Post message to elog [default = False]
            For ascan, info
        daq : bool
            Use daq [default = True]
        record : bool
            Record daq [default = True]
        config : bool
            Use calib cycles [only relevent if ascan = False]
        set_sequencer : bool
            Reset sequencer with simple 1 step daq event code 187        

        """
        import numpy as np

        step = (end-start)/float(steps)
        delays = np.arange(start,end,step)
        nsteps = len(delays)
        ttotal = nsteps*(events/self.laser.rate+5)
        ntotal_events = events*nsteps
        att = env.att_dia
        
        if set_sequencer:
            env.event.modeNtimes(events)
            self.laser.set_sequencer()
       
        if daq:
            env.daq.reco = record
            if not ascan:
                if config:
                    env.daq.configure(events=events)
                else:
                    env.daq.begin(events=ntotal_events)

        message = 'Delay Scan from {:} to {:} with {:} steps'.format(start,end,nsteps)
        print(message)

        if comment:
            message += comment+'\n'

        if ascan:
            env.daq.ascan(self.delay, start, end, nsteps, events, sequencer=events)
            
            runnum = env.daq.runnumber()
            if env.daq.isRecording() and post is not False:
                self.elog.submit(message, runnum=runnum)

        else:
            
            try:
                msg = '{:4} {:>8} {:>10} {:>10}'.format('Step', 'Energy', 'Atten', 'Delay')
                print(msg)
                message += msg+'\n' 
                
                msg = '-'*37
                print(msg)
                message += msg+'\n' 
                
                for istep, delay in enumerate(delays):
                   
                    self.laser.set_delay(delay, quiet=True)

                    if config:
                        time.sleep(2)
                    
                    msg = '{:4} {:8.3f} {:10.3g} {:10.3f}'.format(istep, att._Lusiatt__E, 
                            att.getTvalue(), self.laser.delay)
                    print(msg)
                    message += msg+'\n' 
                    
                    if daq and config:
                        env.daq.calibcycle(events=events, use_sequencer=events)
                        env.daq.wait()
                    else:
                        time.sleep(events/120.)
                    
            except KeyboardInterrupt:
                message += 'Aborting scan...'

            runnum = env.daq.runnumber()
            if env.daq.isRecording() and post is not False:
                self.elog.submit(message, runnum=runnum)

            env.daq.wait()
            env.daq.endrun()
            time.sleep(3)


class Laser(object):
    """Laser class.
    """

    def __init__(self):
        """Initialize experiment.
           pacemaker_delay0: time_zero delay of pacemaker trigger [default=748917.9 ns]
           inhibit_offset: inhibit trigger time before pacemaker trigger [default=500000 ns, i.e., 0.5 ms]
           xray_delay0: x-ray arrival time zero.
        """
        self.shutter_opo = Shutter('CXI:LAS:SHT:02:CMD')
        self._laser_delay = Pv.Pv('LAS:FS5:VIT:FS_TGT_TIME_DIAL')

    def get_delay(self, **kwargs):
        """Get Laser delay in ns.
        """
        return self._laser_delay.get()
 
    def set_delay(self, delay, quiet=False, reset=True, **kwargs):
        """Set Laser delay in ns.
        """
        return self._laser_delay.put(delay)
 
    @property
    def delay(self):
        """Laser delay in ns.
        """
        return self._laser_delay.get()

    @property
    def delay_str(self):
        delay = self.delay
        if delay >= 1e6:
            return '{:} ms'.format(delay/1.e6)
        elif delay >= 1e3:
            return '{:} us'.format(delay/1.e3)
        elif delay >= 0:
            return '{:} ns'.format(delay)
        else:
            return '{:} ns (AFTER X-ray pulse)'.format(delay)

    def set_sequencer(self):
        """
        Simple set sequencer for cxi daq readout
        """
        env.event.setnsteps(1)
        seqstep = 0
        env.event.setstep(seqstep, 187, 0,fiducial=0,comment=' ');seqstep+=1
        env.event.setSyncMarker(120)
        env.event.update()
        time.sleep(2)

    def clear_sequencer(self):
        """Clear sequencer of old values.
        """
        for seqstep in range(20):
            env.event.setstep(seqstep, 0, 0,fiducial=0,comment=' ');seqstep+=1
        env.event.update()
        time.sleep(2)

    @property
    def rate(self):
        """Rate in Hz.
        """
        return env.event.getSyncMarker()

    @property
    def shutter_status(self):
        shutter_str = 'Shutters: '
        for shutter in ['shutter_opo']:
            shutter_str += str(getattr(self, shutter))+' '
   
        return shutter_str

    def __str__(self):
        return 'Laser Delay = {:}, {:}'.format(self.delay_str, self.shutter_status)

    def __repr__(self):
        return '<{:}>'.format(str(self))

class Shutter(object):
    """Laser Shutter.
    """
    def __init__(self, pv, alias=''):
        import psp.Pv as Pv
        self._name = alias
        self._shutter = Pv.Pv(pv)

    def open(self):
        self._shutter.put(1)
        
    def close(self):
        self._shutter.put(0)

    @property
    def state(self):
        if self._shutter.get() == 1:
            return 'open'
        else:
            return 'close'

    def __str__(self):
        return self.state

    def __repr__(self):
        return '<{:}: {:}>'.format(self._name, self.state)


