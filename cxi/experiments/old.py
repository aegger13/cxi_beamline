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

    def scan_delay(self, events=120, start=-1, end=60, step=0.020, 
            daq=True, calib=True,
            post=None, quiet=False, comment=None, set_sequencer=True, **kwargs):
        """Make a daq run.
        """
        import numpy as np
        delays = np.arange(start,end,step)
        nsteps = len(delays)
        ttotal = nsteps*(nevents/self.laser.rate+5)
        ntotal_events = events*nsteps
        
        if set_sequencer:
            env.event.modeNtimes(events)
            self.laser.set_sequencer()

        if daq:
            env.daq.record = record
            if config:
                env.daq.begin(events=events)
            else:
                env.daq.begin(events=ntotal_events)
        
        if daq:
            if config:
                env.daq.wait()
            runnum = env.daq.runnumber()
        else:
            runnum = None

        if env.daq.isRecording():
            print 'Run {:}: Recording {:} events.'.format(runnum, events)
            message = "Run {:}: \n".format(runnum)
        else:
            print 'Acquiring {:} events.'.format(events)
            message = "Data Collection Test. \n"

        if comment:
            message += comment+'\n'

        message += str(self.laser)

        try:
            for delay in delays:
               
                self.laser.set_delay(delay, quiet=True)

                if config:
                    time.sleep(2)
                
                message('{:4} {:8.2f} {:10.3g}  {:}'.format(i+1, env.att._Lusiatt__E, 
                        env.att.getTvalue(), [int(f.isin()) for f in env.att.filters[:-1]]))
                
                if daq and config:
                    env.daq.calibcycle(events=events)
                    env.event.start()
                    env.daq.wait()
                else:
                    time.sleep(events/120.)
                
        except KeyboardInterrupt:
            message('Aborting scan...')

        if env.daq.isRecording() and post is not False:
            self.elog.submit(message, runnum=runnum)
        else:
            print message

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


