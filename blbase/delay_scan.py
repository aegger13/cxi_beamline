from threading import Thread
import multiprocessing as mp
import time
import datetime
import traceback
import iterscan
import usb_encoder
from psp import Pv
from blutil import notice, printnow
from blbase.motor import Motor

class DelayScan(object):
    """
    Class to facilitate scanning the new delay stage.
    """
    def __init__(self, daq, motor, base_motor, hutch=None, aliases=None, channel=None, encoder_det=None, pvbase=None):
        self._daq = daq
        self.motor = motor
        if not None in (hutch, aliases, channel):
            self._encoder = usb_encoder.UsbEncoder(hutch, *aliases)
            self.config = getattr(self._encoder, "ch{}".format(channel))
        if encoder_det is not None:
            self.encoder_det = encoder_det
        if pvbase is not None:
            self._pvset = Pv.Pv('%s:CH%d:ZEROCNT'%(pvbase,channel))
            self._pvpos = Pv.Pv('%s:CH%d:POSITION'%(pvbase,channel))
            self._pvoffset = Pv.Pv('%s:CH%d:OFFSET'%(pvbase,channel))
            self._pvscale = Pv.Pv('%s:CH%d:SCALE'%(pvbase,channel))
            self.set_zero = self._set_epics_zero
        else:
            self.set_zero = self._set_daq_zero
        self.empty_scan = EmptyScan(motor, base_motor)
        self._base_motor = base_motor

    def commit(self):
        if hasattr(self, "_encoder"):
            self._encoder.commit()
        else:
            print "USB Encoder config not initialized."

    def _set_epics_zero(self, use_offset=False):
        """
        Set the counter for the delay readback such that this
        point is zero. Only works for IOC based usb encoders. It
        does this but zeroing the usdusb4 box's internal counter.

        use_offset: uses the IOC's equivalent of the DAQ offset
            field to zero the delay stage position instead of
            zeroing the dial.
        """
        if hasattr(self, "_pvset"):
            if use_offset:
              self._pvoffset.put(self._pvoffset.get() - int(self._pvpos.get()/self._pvscale.get()))
            else:
              self._pvset.put(1)
              self._pvoffset.put(0)
        else:
            print "Needs a base PV for usb encoder to zero it via epics."

    def _set_daq_zero(self, take_daq=True, zero_readback=None):
        """
        Set the offset for the delay readback in the daq such that this
        point is zero. Needs the daq to be running, so by default connects
        to the daq and starts a no-record run.

        take_daq: bool, set to False to skip connecting to the daq.
        zero_readback: int amount at our new zero position.
            Leave at None to retrieve value from pyami.
        """
        if hasattr(self, "config"):
            if zero_readback is None:
                if hasattr(self, "encoder_det"):
                    if take_daq:
                        prev_record = self._daq.record
                        self._daq.record = False
                        self._daq.connect()
                        self._daq.configure(duration=2)
                        self._daq.begin(duration=2)
                    try:
                        self.encoder_det.connect()
                        self.encoder_det.clear()
                    except Exception:
                        traceback.print_exc()
                        print "Unknown error in pyami. Please restart the daq and try again."
                        return
                    time.sleep(0.5)
                    d = self.encoder_det.get()
                    if take_daq:
                        self._daq.endrun()
                        self._daq.record = prev_record
                    if d["time"] > 1:
                        zero_readback = int(round(d["mean"]))
                    else:
                        print "No events captured by pyami encoder..."
                        return
                else:
                    print "Needs encoder_det pyami obj to retrieve offset"
                    return
            self.config.set_offset(-zero_readback, commit=True)
            if take_daq:
                self._daq.configure()
                self._daq.disconnect()
            print "Done setting daq zero for usb encoder"
        else:
            print "Needs usb encoder config; not initialized."

    def __call__(self, points, events=None, duration=None, use_l3t=False):
        """
        Scan the new delay stage, live. Assumes the daq is configured.
        
        Parameters:
        points: an array of 2 points to scan back and forth between. 
        events: the number of events to take in the scan.
        duration: the length of time of the scan in seconds. 
            Either events or duration needs to be specified, but not both. If
            both are specified, use duration.
        use_l3t: use the l3t filter or not
        """
        self.delay_scan(points, events, duration, use_l3t)

    def delay_scan(self, points, events=None, duration=None, use_l3t=False):
        """
        Scan the new delay stage, live. Assumes the daq is configured.

        Parameters:
        points: an array of 2 points to scan back and forth between.
                can also specify a long array to go from first point to
                second to third, etc., wrapping around to the first
        events: the number of events to take in the scan.
        duration: the length of time of the scan in seconds.
            Either events or duration needs to be specified, but not both. If
            both are specified, use duration.
        use_l3t: use the l3t filter or not
        """
        if self.empty_scan.is_scanning():
            print "Stopping empty scan..."
            self.empty_scan.stop()
        try:
            print "Configuring daq..."
            self._daq.feedback.connect()
            self._daq.configure(events=events, duration=duration, use_l3t=use_l3t)
            self._daq.write_feedback_pvs([self.motor],[points],0,0)

            printnow("Initializing delay scan...")
            in_pipe, out_pipe = mp.Pipe()
            daq_proc = mp.Process(target=daq_watch_thread, args=(self._daq, out_pipe,))
            hooks = DelayScanHooks(in_pipe, self._daq, daq_proc, events, duration, use_l3t)
            scan = iterscan.IterScan(self.motor, cycle_gen(points, self.motor), hooks)
            scan.do_print = False
            print "done."
            scan.scan()
            daq_proc.join()
        except KeyboardInterrupt:
            pass
        finally:
            with IgnoreKeyboardInterrupt():
                print "Cleaning up delay scan..."
                time.sleep(0.5)
                print "Cleaning EPICS feedback fields..."
                self._daq.feedback.cleanFields()
                print "Stopping daq run..."
                self._daq.endrun()
                print "Delay scan complete"

    def set_speed(self, value):
        return self._base_motor.set_speed(value)
    set_speed.__doc__ = Motor.set_speed.__doc__


def daq_watch_thread(daq, out_pipe):
    """
    Watches the daq, waits for it to be done. Sends a message out when done.
    """
    daq.wait()
    out_pipe.send("daq_done")

def cycle_gen(points, motor):
    """
    Infinite generator that returns each entry in points, then returns to the
    first entry when we run out of points.

    Aborts if we try to yield a point outside of the motor's limits.
    """
    while True:
        for pt in points:
            if point_ok(pt, motor):
                yield pt
            else:
                print "Recieved bad point: outside of limits! Stopping!"
                raise GeneratorExit()

def point_ok(point, motor):
    low = motor.get_lowlim()
    high = motor.get_hilim()
    return low < point < high

class DelayScanHooks(iterscan.Hooks):
    """
    Receives message from daq_watch_thread to stop iterscan object
    when daq is done
    """
    def __init__(self, in_pipe, daq, daq_proc, events, duration, use_l3t):
        self.in_pipe = in_pipe
        self.daq = daq
        self.daq_proc = daq_proc
        self.events = events
        self.duration = duration
        self.use_l3t = use_l3t
        self.timer_thread = Thread(target=self.time_update_loop, args=())

    def pre_scan(self, scan):
        iterscan.Hooks.pre_scan(self, scan)
        printnow("Moving motor to start position...")
        scan.to_first_point()
        scan.wait()
        print "done."
        print "Starting daq and beginning delay scan."
        self.daq.begin(events=self.events, duration=self.duration, use_l3t=self.use_l3t)
        self.start_timer()
        self.daq_proc.start()
        self.timer_thread.start()

    def post_scan(self, scan):
        with IgnoreKeyboardInterrupt():
            try:
                # Raises AttributeError if proc never started (race condition)
                self.daq_proc.terminate()
            except AttributeError:
                pass
            try:
                # Raises RuntimeError if thread never started (race condition)
                self.timer_thread.join()
            except RuntimeError:
                pass
            printnow("Returning motor to pre-scan position...")
            iterscan.Hooks.post_scan(self, scan)
            print "done."

    def post_step(self, scan):
        while self.in_pipe.poll():
            msg = self.in_pipe.recv()
            self.msg_react(msg, scan)

    def msg_react(self, msg, scan):
        if msg == "daq_done":
            self.update_time_elapsed()
            print "Daq is done."
            scan.abort_scan("")

    def start_timer(self):
        self.t0 = datetime.datetime.now()

    def get_time_elapsed(self):
        delta = datetime.datetime.now() - self.t0
        return delta.total_seconds()

    def update_time_elapsed(self):
        s_total = round(self.get_time_elapsed(), 2)
        notice("Delay scan time elapsed: {}".format(s_total))

    def time_update_loop(self):
        while self.daq_proc.is_alive():
            self.update_time_elapsed()
            time.sleep(0.01)

class EmptyScan(object):
    """
    Moves the delay stage as if a scan is happening, but does not connect to
    the daq in any way. Useful if you'd like to run a different scan at
    many different delays.
    """
    def __init__(self, motor, base_motor):
        self._motor = motor
        self._base_motor = base_motor
        self._thread = None

    def is_scanning(self):
        """
        Return true if an empty scan is active.
        """
        return (self._thread is not None and self._thread.is_alive()) or not self._base_motor.get_par("done_moving")

    def start(self, points):
        """
        Move the stage indefinitely in the background.
        """
        if not self.is_scanning():
            self._thread = Thread(target=self._scan, args=(points,))
            self._thread.start()

    __call__ = start

    def stop(self):
        """
        If an empty scan is going, stop it.
        """
        if self.is_scanning():
            self._base_motor.put_par("spg", 0)
            try:
                self._thread.join()
            except:
                pass
            self._thread = None
            time.sleep(1)
            self._base_motor.put_par("spg", 2)

    def _scan(self, points):
        """
        Run an "infinite" (interruptable) empty scan.
        """
        scan = iterscan.IterScan(self._motor, cycle_gen(points, self._motor), EmptyScanHooks(self._base_motor))
        scan.do_print = False
        scan.scan()

class EmptyScanHooks(iterscan.Hooks):
    def __init__(self, base_motor):
        self.base_motor = base_motor

    def pre_scan(self, scan):
        iterscan.Hooks.pre_scan(self, scan)
        self.base_motor.put_par("spg", 2)

    def pre_step(self, scan):
        self.check_motor(scan)

    def post_scan(self, scan):
        self.base_motor.put_par("spg", 2)
        iterscan.Hooks.post_scan(self, scan)

    def check_motor(self, scan):
        if self.base_motor.get_par("spg") == 0:
            scan.abort_scan("")


class IgnoreKeyboardInterrupt(object):
    """
    Use as an object in a with statement to disable ctrl+c in a block of code.
    If called in a background thread, signal.signal throws value error. Skip
    the commands in this case, since we don't care about sigint in a thread
    anyway.
    """
    def __enter__(self):
        """
        Start ignoring sigint, store old handler for later
        """
        try:
            self.sig = signal.signal(signal.SIGINT, signal.SIG_IGN)
        except Exception:
            pass

    def __exit__(self, type, value, traceback):
        """
        Restore sigint.
        """
        try:
            signal.signal(signal.SIGINT, self.sig)
        except Exception:
            pass

