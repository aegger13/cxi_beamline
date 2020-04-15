import os
import time
import traceback
import datetime
import numpy as np
import random
import psp.Pv as Pv
import blbase.daq
from blbase.motor import Motor
from blbase.virtualmotor import VirtualMotor
from pswww import pypsElog
import beamline as env

expname = os.path.basename(__file__).split(".")[0]

class pi_velocity_context(object):
    def __init__(self, pimotor, velocity):
        self.pimotor = pimotor
        self.velocity = velocity
        self.original_velocity = pimotor.get_velocity()
  
    def __enter__(self):
        self.pimotor.set_velocity(self.velocity)
  
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pimotor.set_velocity(self.original_velocity)

class ims_speed_context(object):
    def __init__(self, imsmotor, speed):
        self.imsmotor = imsmotor
        self.speed = speed
        self.original_speed = imsmotor.get_speed()
  
    def __enter__(self):
        self.imsmotor.set_speed(self.speed)
  
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.imsmotor.set_speed(self.original_speed)

class GroupAtten(object):
    """
    Group together Feeatt and Lusiatt.
    """
    def __init__(self, PVbase, 
#            fee_filts=[], lusi_filts=[0,2,3,4,5,6,7],
#            fee_filts=[3,4], lusi_filts=[0,2,3,4,5],
            fee_filts=[3,4,5,6], lusi_filts=[3,4,5],
#            fee_filts=[3,4,5,6,7], lusi_filts=[4,5],
            eswitch=12.8, n_att=None):
        from blinst import linac
        from blinst import feeatt
        from blinst import lusiatt
        self._fee_filts = fee_filts
        self._lusi_filts = lusi_filts
        lcls_linac = linac.Linac()
        self._feeatt = feeatt.Feeatt(lcls_linac)
        self._lusiatt = lusiatt.Lusiatt(PVbase, eswitch=eswitch, n_att=n_att)

    @property
    def nattenuators(self):
        """
        Combined list of selected fee and lusi filters
        """
        return len(self.filters)
 
    @property
    def filters(self):
        """
        Combined list of selected fee and lusi filters
        """
        flist = []
        for i in self._fee_filts:
            flist.append(Filter(self._feeatt.att[i]))
        for i in self._lusi_filts:
            flist.append(Filter(self._lusiatt.filters[i]))
        return flist

    def get_ftrans(self, E):
        return {f: f.transmission(E) for f in self.filters}

    def getTvalue(self):
        return self._feeatt.getTvalue()*self._lusiatt.getTvalue()

    def getE(self):
        return self._feeatt.getE()

    def set_atten(self, alist, nofee=False, wait=True):
        """
        Set list of attenuators
        """
        if len(alist) > len(self.filters):
            print('Error setting too long of attenuator list {:}'.format(alist))
            return

        for iatten, val in enumerate(alist):
            if val:
                self.filters[iatten].movein(nofee=nofee)
            else:
                self.filters[iatten].moveout(nofee=nofee)
        if wait:
            self.wait()
            
    def get_atten_list(self, detailed_scan=False, single_attenuators=False,
                             nattenuators=None):
        """
        Get attenuation list
        """
        if not nattenuators:
            nattenuators = self.nattenuators

        atten_list = []
        if detailed_scan:
            for i in range(2**nattenuators):
                atten_list.append(self._get_atten_logic(i,nattenuators=nattenuators))
        
        else:
            for i in range(nattenuators+1):
                alist = []
                for j in range(nattenuators):
                    if j < i:
                        if single_attenuators and j < i-1:
                            alist.append(0)
                        else:
                            alist.append(1)
                    else:
                        alist.append(0)
                atten_list.append(alist)

        return atten_list

    def _get_atten_logic(self, ibits, nattenuators=None):
        if not nattenuators:
            nattenuators = self.nattenuators 
        nattens = len(bin(ibits))-2
        a = []
        for i in range(nattenuators):
            if i < nattens and int(bin(ibits)[-i-1]) == 1:
                a.append(1)
            else:
                a.append(0)
        return a    

    def allIN(self, wait=None):
        """
        Move all out
        """
        self._feeatt.allIN()
        self._lusiatt.allIN()
        if wait:
            self._feeatt.wait()
        if wait:
            self._lusiatt.wait()
#        for f in self.filters:
#            f.movein()
#        if wait:
#            self.wait()

    def allOUT(self, wait=None):
        """
        Move all out
        """
        self._feeatt.allOUT()
        self._lusiatt.allOUT()
        if wait:
            self._feeatt.wait()
        if wait:
            self._lusiatt.wait()
#        for f in self.filters:
#            f.moveout()
#        if wait:
#            self.wait()

    def wait(self, sleep=1):
        """
        Wait for all to finish move
        """
        for f in self.filters:
            f.wait()
        if sleep:
            time.sleep(sleep)

    def atten_check(self, atten_list, energy=None):
        """
        Check attenuation for atten_list
        """
        if not energy:
            energy = self.getE()
        atrans = []
        for ilist, alist in enumerate(atten_list):
            trans = 1.
            for iatten, val in enumerate(alist):
                if val:
                    trans *= self.filters[iatten].transmission(energy)
            atrans.append(trans)
            print('{:4} {:20} {:10.3g}'.format(ilist, alist, trans))
        return atrans

    def attenuation_scan(self, events=240, daq=True, config=True,
                            atten_list=None, nofee=True, 
                            detailed_scan=False, single_attenuators=False, nattenuators=None, 
                            post=False, record=None, title=None, ignore_mirror=False):
        """Attenuation Calibration
            events: Number of events to record for each attenuator setting
            nattenuators: number of attenuators to scan over [default=9]
            detailed_scan:  Scan over all attenuator settings for nattenuators
            single_attenuators [default=False]:
                True:  Calibration cycles with sequentially inserted filters starting with no filters.
                False: Calibration cycles with sequentially inserted and leaving in filters starting with no filters.
            record:  this controls the recording state of the daq.
        """
        import beamline as env
        from pswww import pypsElog
        elog = pypsElog.pypsElog()
        self.allOUT()
        if not nattenuators:
            nattenuators = self.nattenuators 

        if atten_list:
            runtype = 'Attenuation Scan: Scan from custom attenuation list.'
        else:
            atten_list = self.get_atten_list(detailed_scan=detailed_scan,
                                single_attenuators=single_attenuators, nattenuators=nattenuators)
            if detailed_scan:
                runtype = 'Attenuation Scan: Detailed scan of every attenuator combination.'
            elif single_attenuators:
                runtype = 'Attenuation Scan: Sequentially inserted filters starting with no filters.'
            else:
                runtype = 'Attenuation Scan: Sequentially inserted and leaving in filters starting with no filters.'

        nsteps = len(atten_list)
        ntotal_events = events*nsteps
        time.sleep(2)
        if daq:
            env.daq.record = record
            if config:
                env.daq.begin(events=events)
                env.daq.wait()
            else:
                env.daq.begin(events=ntotal_events)
          
            run_num = env.daq.runnumber()
        else:
            run_num = None

        if title:
            msg = '{:}\n'.format(title)
            msg += '{:}\n'.format(runtype)
        else:
            msg = '{:}\n'.format(runtype)
        msg += '\n'
        sformat = '-->  x.attenuation_scan(events={:}, detailed_scan={:}, single_attenuators={:}, ' 
        sformat += 'nattenuators={:}, post={:}, record={:}, title={:})\n'
        msg += sformat.format(events,detailed_scan,single_attenuators,nattenuators,post,record,title)
        msg += '\n'
        msg += '{:4} {:8} {:10}  {:}\n'.format('Step', 'E_keV', 'Trans', 'Attenuator_list')
        msg += '-'*60+'\n'
        try:
            for alist in atten_list:
                self.set_atten(alist, nofee=nofee, wait=True)
                if config:
                    time.sleep(2)
                msg += '{:4} {:8.2f} {:10.3g}  {:}\n'.format(i, self.getE(), 
                        self.getTvalue(), [int(f.isin()) for f in self.filters])
                if daq and config:
                    env.daq.calibcycle(events=events)
                    env.daq.wait()
                else:
                    time.sleep(events/120.)

            if daq:
                run_num = env.daq.runnumber()
                env.daq.endrun()
            
        except KeyboardInterrupt:
            msg += 'Aborting scan...\n'
        
        if post:
            elog.submit(log, runnum=runnum)
        time.sleep(1)    

class Filter(object):
    _filt_attrs = ['isin','isout','wait']
    def __init__(self, filt_obj):
        self._filter = filt_obj
        self._type = self._filter.__module__.split('.')[1]

    def att_len(self, E):
        """
        Attenuation length [m]; E in keV
        """
        if self._type == 'feeatt':
            return self._filter.att_len(E)
        else:
            import blutil.attenuators as utilAtt
            return utilAtt.attenuation_length(self._filter.material(), energy=E)[0]
    
    def transmission(self, E):
        """
        Transmission; E in keV
        """
        if self._type == 'feeatt':
            return self._filter.transmission(E)
        else:
            import numpy as np
            return np.exp(-self._filter.d()/1.e6/self.att_len(E))

    def moveout(self, nofee=False):
        """
        Move attenuator out
        """
        if nofee and self._type == 'feeatt':
            return
        else:
            self._filter.moveout()

    def movein(self, nofee=False):
        """
        Move attenuator in
        """
        if nofee and self._type == 'feeatt':
            return
        else:
            self._filter.movein()

    def __getattr__(self, attr):
        if attr in self._filt_attrs:
            return getattr(self._filter, attr)

    def __repr__(self):
        return self.status()

    def __dir__(self):
        all_attrs = set(self._filt_attrs +
                        self.__dict__.keys() + dir(Filter))

        return list(sorted(all_attrs))
    
    @property
    def PVbase(self):
        if self._type == 'feeatt':
            return self._filter.pv
        else:
            return self._filter.PVbase

    def status(self):
        from blutil import estr
        if self._type == 'feeatt':
            s = "attenuator %s (%d um of %s) is in position: "%(self.PVbase, 
                    self._filter.d*1.e6, str(self._filter.material))
            if self.isin():
              s += estr("IN",color="green",type="normal")
            elif self.isout():
              s += estr("OUT",color="green",type="normal")
            else:
              s += estr("Unknown",color="yellow",type="normal")
            return s
        else:
            return self._filter.status()


class Experiment(object):
    """
    Fly and mesh scan experiment class.
    """
    def __init__(self):
        self.expname = expname[3:]
        self.elog = pypsElog.pypsElog()
        user_motors = [ 
                        ["CXI:PI2:MMS:01","Sample_x"],
                        ["CXI:PI2:MMS:02","Sample_y"],
                        ["CXI:PI2:MMS:03","Sample_z"],
                      ]
        env.motors.add( *user_motors,  group="user") 
        for item in user_motors:
            alias = item[1]
            setattr(self, alias, getattr(env.motors.all.m, alias))

        self.vernier = env.vernier
        self.gasdet_sig = Pv.Pv('GDET:FEE1:241:ENRC')
        self.center = 125
        self.pp = env.pp
        self.event = env.event
        #env.daq.add_readout_checks("Sc2Epix","Sc2Imp")
        env.daq.add_readout_checks("Sc2Imp")
        self.att = GroupAtten("XRT:DIA:ATT")
        self.atten_list = [
                [0,0,0,0,0,0,0],
                [1,0,0,0,0,0,0],
                [0,1,0,0,0,0,0],
                [0,0,1,0,0,0,0],
                [1,0,1,0,0,0,0],
                [0,1,1,0,0,0,0],
                [1,1,1,0,0,0,0],
                [0,0,0,1,0,0,0],
                [0,1,0,1,0,0,0],
                [0,0,1,1,0,0,0],
                [1,1,1,1,0,0,0],
                [0,0,0,0,1,0,0],
                [0,0,1,0,1,0,0],
                [0,0,1,1,1,0,0],
                [0,0,0,0,0,1,0],
                [0,0,0,1,0,1,0],
                [0,1,1,1,0,1,0],
                [0,1,0,0,1,1,0],
                [0,0,0,1,1,1,0],
                [0,1,1,1,1,1,0],
                [0,0,0,0,0,0,1],
                [0,0,1,1,0,0,1],
                [0,0,0,1,1,0,1],
                [0,0,0,0,0,1,1],
                [0,0,0,1,0,1,1],
                ]

    def monitor(self, picker=None, beam_rate=30):
        """
        Monitor continuously at beam_rate (default=30 Hz) 
        """
        if picker is not None:
            self.set_sequencer_single(picker=picker, beam_rate=beam_rate)
        self.event.modeForever()
        self.event.start()

    def shoot_and_move(self, tweek=0.065, picker=None):
        """
        Take one shot and step the x motor by tweek.
        If picker set to True or False set accordingly -- otherwise assume sequencer is as desired
        """
        if not self.event.getmode() == 'Once':
            print('Setting sequencer modeOnce...')
            self.event.modeOnce()
        if picker==False and self.event.getnsteps() != 1:
            print('Setting sequencer single with picker={:}'.format(picker))
            self.set_sequencer_single(picker=picker)
        elif picker==True and (self.event.getnsteps() != 3 or Pv.get(self.pp._PVname('SE')) != 2):
            print('Setting sequencer single with picker={:}'.format(picker))
            self.set_sequencer_single(picker=picker)
        self.event.start()
        self.event.wait()
        if tweek:
            self.Sample_x.mvr(tweek)
 
    def fly_scan(self, fly_start=None, fly_dist=9.5, dist_per_shot=0.065, 
                       lat_start=None, lat_rows=1, lat_step_size=0.065, 
                       beam_rate=30, reset_motors=False, 
                       next_line=True,
                       gasdet_min=-1., accwait=0.1, transition_time=0.1, 
                       atten_list=None, nofee=False,
                       vernier_list=None,
                       detailed_scan=False, single_attenuators=False, nattenuators=None, 
                       title=None, post=True, record=None, verbose=False):
        """
        Fly scan

        Parameters
        ----------
        fly_start : float
            Fly scanning start position (Sample_x motor axis) [Default = current position]
        fly_dist : float
            Fly scanning distance (Sample_x motor axis) [default = 10 mm]
        dist_per_shot : float
            Distance per shot [Default = 0.065 mm]
        lat_start : float
            Lateral (Sample_y) axis start position [Default = current position]
        lat_rows : int
            Number of lateral rows to fly scan [Default = 2]
        lat_step_size : float
            Step size between rows to fly scan [Default = 0.065 mm]
        beam_rate : float
            Beam rate [Hz] (Default=120)
        post : bool
            Post to elog if recorded [Default = True]
        gasdet_min:  float
            minimum gas detector value (GDET:FEE1:241:ENRC) to start a row [mJ] (default: -1)
        accwait : float
            Time to wait for scan motor to accelerate [Default=0.1 sec]
        transition_time : float
            Extra transition time to wait on top of 2*accwait [Default=0.1 sec]
        reset_motors : bool
            Reset motors to original positions
        next_line : bool 
            Goto next line to prepare for next fly scan
        vernier_list : bool or list
            Vernier list to scan over.
        atten_list : bool or list
            Attenuator list to scan over.  If True use default in x.atten_list
        detailed_scan : bool
            Scan over all attenuator settings (for max nattenuators if set)
        single_attenuators : bool
            Sequentially inserted filters starting with no filters.
        nattenuators: int
            number of attenuators to scan over [default=all filters]
        record:  bool
            This controls the recording state of the daq.
            * True:  force recording of the run.
            * False: force off recording of the run.
            * None:  use the option selected in the daq gui (default).
        
        """
        daq = env.daq
        fly_motor = self.Sample_x
        lat_motor = self.Sample_y
        comp_motor = self.Sample_z
       
        fly_original = fly_motor.wm()
        lat_original = lat_motor.wm()
        
        if not fly_start:
            print "Starting motor {0} at current position {1}...".format(fly_motor, fly_original)
            fly_start = fly_original
        else:
            print "Moving motor {0} to starting position {1}...".format(fly_motor, fly_start)
            fly_motor.mv(fly_start)
        
        if not lat_start:
            print "Starting motor {0} at current position {1}...".format(lat_motor, lat_original)
            lat_start = lat_original
        else:
            print "Moving motor {0} to starting position {1}...".format(lat_motor, lat_start)
            lat_motor.mv(lat_start)

        fly_end = fly_start+fly_dist

        if atten_list:
            if atten_list is True:
                atten_list = self.atten_list
                print "Using default attenuation list for {:} scans".format(len(atten_list))
                if not title:
                    title = "Default attenuation list {:} scans".format(len(atten_list))
            else:
                print "Using custom attenuation list for {:} scans".format(len(atten_list))
                if not title:
                    title = "Custom attenuation list {:} scans".format(len(atten_list))
        elif single_attenuators: 
            atten_list = self.att.get_atten_list(single_attenuators=True, nattenuators=nattenuators)
            print "Using single attenuation list for {:} scans".format(len(atten_list))
            if not title:
                title = "Single attenuation list {:} scans".format(len(atten_list))
        elif detailed_scan: 
            atten_list = self.att.get_atten_list(detailed_scan=True, nattenuators=nattenuators)
            print "Using detailed attenuation list for {:} scans".format(len(atten_list))
            if not title:
                title = "Detailed attenuation list {:} scans".format(len(atten_list))
        elif vernier_list:
            print "Using vernier energy list for {:} scans".format(len(vernier_list))
            if not title:
                title = "Vernier Energy list {:} scans".format(len(vernier_list))
        else:
            print "Setting up for {:} scans with current attenuation".format(lat_rows)

        if atten_list:
            lat_rows = len(atten_list)
        elif vernier_list:
            lat_rows = len(vernier_list)

        if title:
            log = title+'\n'
        else:
            log = ""

        slog = "#\n# x.fly_scan(fly_start={:}, fly_dist={:}, dist_per_shot={:}, " \
                +"lat_start={:}, lat_rows={:}, lat_step_size={:}, " \
                +"beam_rate={:})\n"
        log += slog.format(fly_start, fly_dist, dist_per_shot, 
                           lat_start, lat_rows, lat_step_size, 
                           beam_rate)
        log += "#\n# " + self.sample_status() + "\n#\n"
        print(log)
        daq.starttime = datetime.datetime.now()
   
        if atten_list:
            print "Starting fly_scan for {:} attenuation settings".format(lat_rows)
        else:
            print "Starting fly_scan for {:} rows".format(lat_rows)

        last_pos, next_pos = fly_start, fly_end
        print "Connecting to daq..."
        daq.connect()
        # remember record state and set it back at end
        record_state = daq.record
        velocity = dist_per_shot * beam_rate
        tshots = abs((fly_end-fly_start)/velocity)-2*accwait-transition_time
        nshots = int(beam_rate*tshots)
        
        if beam_rate <= 30:
            print("Setting beam_rate = {:} Hz".format(beam_rate))
            self.event.modeNtimes(nshots)
            self.set_sequencer_single(beam_rate=beam_rate)
        elif beam_rate == 120:
            print("ERROR: 120 Hz beam_rate not yet implemented".format(beam_rate))
            return 
        else:
            print("ERROR: {:} Hz beam rate is not possible -- only <= 30 Hz".format(beam_rate))
            return 
       
        daq.record = record
        config_details = dict(
            events=0,
            use_l3t=True)
        print "Configuring daq..."
        daq.configure(**config_details)
        
        base_pts = [ lat_start + i*lat_step_size for i in range(lat_rows) ]
        lat_pts = base_pts
        next_base = base_pts[0]
        next_lat = lat_pts[0]
   
        if atten_list:
            self.att.allOUT(wait=True)

        with blbase.daq.EpicsFeedbackContext(daq.feedback):
            daq.write_feedback_pvs((lat_motor, fly_motor), lat_pts, 0, 0)
            fly_motor.wait()
            lat_motor.wait()
            comp_motor.wait()  
            time.sleep(2) # avoid weird issues with data at the start of the scan
            print "Begin scan:"
            try:
                #with pi_velocity_context(fly_motor, velocity):
                with ims_speed_context(fly_motor, velocity):
                    time.sleep(2) # deal with the daq being slow to start taking data
                    for i in range(lat_rows):
                        if atten_list:
                            self.att.set_atten(atten_list[i], nofee=nofee, wait=True)
                        elif vernier_list:
                            self.vernier.mv(vernier_list[i])

                        txt = "Row {0} of {1}, {2} to {3} at {4}"
                        msg = txt.format(i+1, lat_rows, fly_motor, next_pos, lat_motor)
                        print msg
                        daq.write_feedback_step_pvs(i)
                        
#                        config_details = dict(
#                            events=nshots,
#                            use_l3t=True)
#                        
                        while self.gasdet_sig < gasdet_min:
                            time.sleep(1.)
                            lmsg = "Low beam = {:} mJ -- Waiting for beam to return ...\n".format(self.gasdet_sig)
                            print lmsg
                            log += "# " + lmsg + "\n"
                        
                        if verbose: 
                            print('...start daq for {:} shots'.format(nshots))
                        daq.begin(events=nshots)
                        if verbose: 
                            print('...start motor to {:}'.format(next_pos))
                        fly_motor.mv(next_pos)
                        time0 = time.time()
                        # Wait for acceleration to start shooting
                        time.sleep(accwait)
                        if verbose: 
                            print('...start sequencer {:} sec later'.format(time.time()-time0))
                        self.event.start() 
                        last_pos, next_pos = next_pos, last_pos
                        daq.wait()
                        print('...{:} shots complete for trans={:7.3g}'.format(nshots, self.att.getTvalue()))
                        log += "# {:}, {:} shots at E={:5} eV, trans={:7.3g}\n".format(msg, \
                                        nshots, self.att.getE()*1000., self.att.getTvalue())
                        if fly_motor.ismoving():
                            time0 = time.time()
                            fly_motor.wait()
                            if verbose: 
                                print('...motor stopped {:} sec later'.format(time.time()-time0))
                        else:
                            print('WARNING: Motor finished before shots completed')
                        if verbose: 
                            print('...Line finished')                
        
                        if i == lat_rows-1:
                            break
                        try:
                            next_lat = lat_pts[i+1]
                        except Exception:
                            print "ERROR:  Exception breaking out of fly scan..."
                            break
                        lat_motor.mv(next_lat)
                        lat_motor.wait()

            except Exception:
                self.event.stop()
                self.pp.close()
                traceback.print_exc()
                err = "Error in scan, aborting..."
                log += "#" + err + "\n"
                print err
            except KeyboardInterrupt:
                self.event.stop()
                self.pp.close()
                err = "Scan interrupted by ctrl+c, aborting..."
                log += "#" + err + "\n"
                print err
        try:
            daq.stop()
        except:
            pass
        
        runnum = daq.runnumber()
        if daq.isRecording() and post is not False:
            self.elog.submit(log, runnum=runnum)

        if reset_motors:
            print "Done with fly_scan, return motors to original positions..."
            fly_motor.mv(fly_original)
            lat_motor.mv(lat_original)
        elif next_line:
            print "Done with fly_scan, move motors to next line..."
            fly_motor.mv(fly_original)
            lat_motor.mvr(lat_step_size)
        else:
            print "Done with fly_scan, leaving motors at current positions..."

        daq._Daq__scanstr = log
        daq.savelog()
        daq.record = record_state
        print "Done"

    def set_sequencer_burst(self, Nshots, Nbursts=1):
        # Set up sequencer to do pulse picker
        self.pp.prepare_burst(Nshots,Nbursts=Nbursts,burstMode=True)
        # Make sure sync marker is at 120 Hz... this gets messed up sometimes?
        self.event.setSyncMarker(120)
  
    def set_sequencer_single(self, daq_code=187, beam_rate=30, picker=True):
        """
        Simple set sequencer for cxi daq readout
        """
        #self.clear_sequencer()
        self.event.setSyncMarker(beam_rate)
        if picker:
            self.pp.prepare_FlipFlop(1, readoutCode=187, prePP=2)
        else:
            self.event.setnsteps(1)
            seqstep = 0
            self.event.setstep(seqstep, daq_code, 0,fiducial=0,comment='Daq Readout');seqstep+=1
            self.event.update()
            time.sleep(2)

    def clear_sequencer(self):
        """Clear sequencer of old values.
        """
        for seqstep in range(20):
            self.event.setstep(seqstep, 0, 0,fiducial=0,comment=' ');seqstep+=1
        self.event.update()
        time.sleep(2)

 
    def sample_status(self):
        txt = "sample_x: {:.3f}, sample_y: {:.3f}, sample_z: {:.3f}"
        return txt.format(self.Sample_x.wm(), 
                          self.Sample_y.wm(), self.Sample_z.wm())
  
    @property
    def _playstatus(self):
        """
        Event sequencer play status
        """
        return Pv.get(self.event._EventSequencer__pv_playstatus)
  

