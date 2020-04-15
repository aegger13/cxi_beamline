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


class Experiment(object):
    """
    Fly and mesh scan experiment class.
    """
    def __init__(self):
        self.expname = expname[3:]
        self.elog = pypsElog.pypsElog()
        user_motors = [ 
                        ["CXI:SC2:MMS:05","Sample_x"],
                        ["CXI:SC2:MMS:06","Sample_y"],
                        ["CXI:SC2:MMS:07","Sample_z"],
                        ["CXI:USR:MXM:01","Sample_phi"],
#                        ["CXI:SC2:MMS:07","crystal_x"],
#                        ["CXI:SC2:MMS:08","crystal_y"],
                      ]
#        user_motors = [ 
#                        ["CXI:SC3:MMS:02","Sample_x"],
#                        ["CXI:SC3:MMS:03","Sample_y"],
#                        ["CXI:SC3:MMS:12","Sample_z"],
#                        ["CXI:SC3:MMS:11","Sample_phi"],
#                        ["CXI:SC3:MMS:07","rystal_x"],
#                        ["CXI:SC3:MMS:08","crystal_y"],
#                      ]
        env.motors.add( *user_motors,  group="user") 
        for item in user_motors:
            alias = item[1]
            setattr(self, alias, getattr(env.motors.all.m, alias))

        self.gasdet_sig = Pv.Pv('GDET:FEE1:241:ENRC')
        self.center = 125
        self.pp = env.pp
        self.event = env.event
        #env.daq.add_readout_checks("Sc2Epix","Sc2Imp")
        env.daq.add_readout_checks("Sc2Imp")
    
    def tomo_fly_scan(self, fly_start, fly_end, dist_per_shot, lat_start, lat_rows, 
                            lat_step_size, angle_min, angle_max, numAngles):
        """
        Tomo fly scan -- wrapper to call fly scan.

        Parameters
        ----------
        fly_start : float
            Fly scanning start position (Sample_x motor axis)
        fly_end : float
            Fly scanning end position (Sample_x motor axis)
        dist_per_shot : float
            Distance per shot
        lat_start : float
            Lateral (Sample_y) axis start position
        lat_rows : int
            Number of lateral rows to fly scan
        lat_step_size : float
            Step size between rows to fly scan
        angle_min : float
            Angle min
        angle_min : float
            Angle max
        numAngles : int
            Nomber of angles
        """
        angles = np.linspace(angle_min, angle_max, numAngles)
        for angleTarget in angles:
            
            self.Sample_phi.umv(angleTarget)
            while not self.Sample_phi.at_pos(angleTarget):
                self.Sample_phi.umv(angleTarget)
            print('starting '+str(angleTarget)+' degrees scan')
            self.fly_scan(fly_start, fly_end, dist_per_shot, lat_start, lat_rows, \
                          lat_step_size/np.cos(angleTarget*np.pi/180), angle_compensate=False)
            
            print(str(angleTarget)+' degrees finished')
            time.sleep(2)
            
        print('Tomo scan finished')
  
    def fly_scan(self, fly_start, fly_end, dist_per_shot, lat_start, lat_rows, lat_step_size, \
                       angle_compensate=True, beam_rate=30, reset_motors=False, 
                       gasdet_min=-1., accwait=0.1, transition_time=0.1, 
                       title=None, post=True, record=None, verbose=True):
        """
        Fly scan

        Parameters
        ----------
        fly_start : float
            Fly scanning start position (Sample_x motor axis)
        fly_end : float
            Fly scanning end position (Sample_x motor axis)
        dist_per_shot : float
            Distance per shot
        lat_start : float
            Lateral (Sample_y) axis start position
        lat_rows : int
            Number of lateral rows to fly scan
        lat_step_size : float
            Step size between rows to fly scan
        angle_compensate : bool
            Compensate Sample_z for Sample_phi angle to keep same focus
        beam_rate : float
            Beam rate [Hz] (Default=120)
        post : bool
            Post to elog if recorded
        gasdet_min:  float
            minimum gas detector value (GDET:FEE1:241:ENRC) to start a row [mJ] (default: -1)
        accwait : float
            Time to wait for scan motor to accelerate [Default=0.1 sec]
        transition_time : float
            Extra transition time to wait on top of 2*accwait [Default=0.1 sec]
        record:  bool
            This controls the recording state of the daq.
            * True:  force recording of the run.
            * False: force off recording of the run.
            * None:  use the option selected in the daq gui (default).
        
        """
       
        if title:
            log = title+'\n'
        else:
            log = ""

        slog = "#\n# x.fly_scan({0}, {1}, {2}, {3}, {4}, {5}, angle_compensate={6}, beam_rate={7})\n"
        log += slog.format(fly_start, fly_end, dist_per_shot, lat_start, lat_rows, lat_step_size, 
                          angle_compensate, beam_rate)
        log += "#\n# " + self.sample_status() + "\n#\n"
        env.daq.starttime = datetime.datetime.now()
        fly_motor = self.Sample_x
        lat_motor = self.Sample_y
        comp_motor = self.Sample_z
   
        print "Starting fly_scan."
        fly_original = fly_motor.wm()
        lat_original = lat_motor.wm()
        print "Moving motors {0} and {1} to starting positions {2} and {3}...".format(fly_motor, \
                    lat_motor, fly_start, lat_start)
        fly_motor.mv(fly_start)
        lat_motor.mv(lat_start)
        if angle_compensate:
            comp_motor.mv(self._comp_z(lat_start))
        last_pos, next_pos = fly_start, fly_end
        daq = env.daq
        print "Connecting to daq..."
        daq.connect()
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
        if angle_compensate:
            comp_pts = [ self._comp_z(lat) for lat in base_pts ]
            lat_pts = [ self._new_lat(lat) for lat in base_pts ]
        else:
            lat_pts = base_pts
        next_base = base_pts[0]
        next_lat = lat_pts[0]
    
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
                        txt = "Scanning row {0} of {1}, {2} from {3} to {4} at {5}={6}..."
                        if angle_compensate:
                            msg = txt.format(i+1, lat_rows, fly_motor, last_pos, next_pos, "angle_comp_x", next_base)
                        else:
                            msg = txt.format(i+1, lat_rows, fly_motor, last_pos, next_pos, lat_motor, next_lat)
                        print msg
                        log += "# " + msg + "\n"
                        daq.write_feedback_step_pvs(i)
                        
#                        config_details = dict(
#                            events=nshots,
#                            use_l3t=True)
#                        
                        while self.gasdet_sig < gasdet_min:
                            time.sleep(1.)
                            msg = "Low beam = {:} mJ -- Waiting for beam to return ...\n".format(self.gasdet_sig)
                            print msg
                            log += "# " + msg + "\n"
                        
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
                        if verbose: 
                            print('...shots complete')
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
                            if angle_compensate:
                                next_base = base_pts[i+1]
                                next_comp = comp_pts[i+1]
                        except Exception:
                            print "ERROR:  Exception breaking out of fly scan..."
                            break
                        lat_motor.mv(next_lat)
                        if angle_compensate:
                            comp_motor.mv(next_comp)
                            comp_motor.wait()
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
        
        runnum = env.daq.runnumber()
        if env.daq.isRecording() and post is not False:
            self.elog.submit(log, runnum=runnum)

        if reset_motors:
            print "Done with fly_scan, return motors to original positions..."
            fly_motor.mv(fly_original)
            lat_motor.mv(lat_original)
        else:
            print "Done with fly_scan, leaving motors at current positions..."

        daq._Daq__scanstr = log
        daq.savelog()
        print "Done"

    @property
    def _playstatus(self):
        """
        Event sequencer play status
        """
        return Pv.get(self.event._EventSequencer__pv_playstatus)
  
    def mesh_scan(self, row_start, num_rows, row_step_size, coll_start, num_colls, coll_step_size=None, 
                        events_per_point=10, randomness=0.0, angle_compensate=True, use_l3t=True):
        """
        Mesh scan
        """
        row_motor = self.Sample_x
        coll_motor = self.Sample_y
        comp_motor = self.Sample_z
    
        if coll_step_size is None:
            coll_step_size = row_step_size
    
        row_end = row_start + (num_rows-1)*row_step_size
        coll_end = coll_start + (num_colls-1)*coll_step_size
    
        self.set_sequencer_burst(events_per_point)
    
        if angle_compensate:
            # One row, one collumn
            row = [ row_start + row_step_size*i for i in range(num_rows) ]
            coll = [ coll_start + coll_step_size*i for i in range(num_colls) ]
            # Have row stay in place while coll moves through every position
            row_pts = []
            for pt in row:
                row_pts.extend([pt]*len(coll))
            # Calculate compensation
            comp_pts = [ self._comp_z(lat) for lat in row_pts ]
            row_pts = [ self._new_lat(lat) for lat in row_pts ]
            # Have coll move back and forth
            coll_rev = list(coll) # implicit copy
            coll_rev.reverse()
            coll_pts = []
            for i in range(num_colls):
                if i % 2:
                    coll_pts.extend(coll_rev)
                else:
                    coll_pts.extend(coll)
    
            env.daq.a3scan_with_list(row_motor, row_pts, coll_motor, coll_pts, comp_motor, comp_pts, 
                                     events_per_point, sequencer=True, use_l3t=use_l3t, 
                                     log_data=self.sample_status())
    
        elif randomness>0:
            row = [ row_start + row_step_size*i for i in range(num_rows) ]
            coll = [ coll_start + coll_step_size*i for i in range(num_colls) ]
            # Have row stay in place while coll moves through every position
            row_pts = []
            for pt in row:
                row_pts.extend([pt]*len(coll))
    
            # Have coll move back and forth
            coll_rev = list(coll) # implicit copy
            coll_rev.reverse()
            coll_pts = []
            for i in range(num_colls):
                if i % 2:
                    coll_pts.extend(coll_rev)
                else:
                    coll_pts.extend(coll)
    
            for i in range(len(row_pts)):
                row_pts[i] += (2*random.random()-1)*randomness
    
            for i in range(len(coll_pts)):
                coll_pts[i] += (2*random.random()-1)*randomness
            env.daq.a2scan_with_list(row_motor, row_pts, coll_motor, coll_pts, 
                                     events_per_point, sequencer=True, use_l3t=use_l3t, 
                                     log_data=self.sample_status())
    
        else:
            env.daq.mesh2D( row_motor, row_start, row_end, num_rows-1, 
                            coll_motor, coll_start, coll_end, num_colls-1, 
                            events_per_point, sequencer=True, use_l3t=use_l3t, 
                            log_data=self.sample_status())
    
    def _new_lat(self, lat_orig):
        angle = self.Sample_phi.wm()
        center = self.center
        return (lat_orig-center) * np.cos(angle*np.pi/180) + center
  
    def _comp_z(self, lat_orig):
        angle = self.Sample_phi.wm()
        center = self.center
        return (lat_orig-center) * -np.sin(angle*np.pi/180) + center
  
    def set_sequencer_burst(self, Nshots, Nbursts=1):
        # Set up sequencer to do pulse picker
        self.pp.prepare_burst(Nshots,Nbursts=Nbursts,burstMode=True)
        # Make sure sync marker is at 120 Hz... this gets messed up sometimes?
        self.event.setSyncMarker(120)
  
    def set_sequencer_single(self, daq_code=187, beam_rate=30, picker=True):
        """
        Simple set sequencer for cxi daq readout
        """
        self.clear_sequencer()
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
        txt = "sample_phi: {0:.3f}, sample_x: {1:.3f}, sample_y: {2:.3f}, sample_z: {3:.3f}"
        return txt.format(self.Sample_phi.wm(), self.Sample_x.wm(), 
                          self.Sample_y.wm(), self.Sample_z.wm())
  
  

