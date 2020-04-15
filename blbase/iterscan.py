"""
Module that contains classes for making arbitrary motor scans.

IterScan: Most general version of a scan using iterators.
Hooks: Defines an interface for defining pre_step, post_step, etc.
AbortScan: Exception thrown to end a scan early

is_motor: function to check if a motor is valid for a scan
is_iterable: function to check if an iterator is valid
is_hooks: function to check if a hooks object is valid

A scan is any action that involves moving motors through a series of
positions and taking some action at each point (generally, recording some
value).
"""
import inspect
import itertools
import collections
import traceback
import math

import blbase.motor as motor
import blbase.virtualmotor as vmotor
import blbase.pvmotor as pvmotor


class IterScan(object):
    """
    Most general version of a scan using motor objects and iterators.

    fields:
    curr_step: current step of the running scan
    scan_mode: current scan mode (None, "linear", or "mesh")

    methods:
    .scan(): Begin a scan.
    .scan_mesh(): Begin a mesh scan.
    .test_scan(): Test that iterators yield expected values.
    .test_mesh(): Test that the mesh has expected values.
    .get_motors(): Return a list of motor objects in the scan.
    .get_positions(): Return a list of motor positions.
    .get_iters(): Return a list of iterators in the scan.
    .wait(): Pauses the thread until all motors in scan are done moving.
    .to_first_point(): Moves motors to the first point in the scan.
    .save_positions(): Saves the current positions for later use.
    .restore_saved(): Moves motors to the previously saved positions.
    .get_stats(): Run through all iterators and calculate basic stats.
    .abort_scan(message=""): End a scan in progress, printing message.
    """
    def __init__(self, *args):
        """
        Initialize IterScan's motors, iterators, and hooks.

        *args: motor objects, iterators, and a Hooks object in some order.
            The first motor object corresponds to the first iterator, etc.
            Motors will be moved to the positions returned by their
            iterators. Motors can be grouped in tuples and matched with
            iterators that return tuples to have them move through tuples
            of points together (this may be useful in a mesh scan).
            Arbitrarily nested motors in tuples should also work, provided
            that the nesting is consistent with the iterator returns.
        """
        self.mots = []
        self.iters = []
        self.orig_iters = []
        self._init_default_hooks()
        for arg in args:
            self._process_arg(arg)
        self._check_args()
        self._curr_mesh = []
        self._saved = []
        self.do_print = True
        self.scan_mode = None

    def _scan(self, step):
        """Base scan function"""
        try:
            self.hooks.pre_scan(self)
            self._init_iters()
            self._curr_step = 0
            try:
                while True:
                    self._curr_step += 1
                    step()
                    if self.do_print:
                        self.print_status()
            except (StopIteration, GeneratorExit):
                if self.do_print:
                    print "Reached end of scan."
            except KeyboardInterrupt:
                print "" # Add a newline to separate the ^C text
                if self.do_print:
                    print "Scan interrupted during step {}.".format(self._curr_step)
            except Exception:
                raise
            self._curr_step = None
        except AbortScan:
            if len(AbortScan.message) > 0:
                print AbortScan.message
        except Exception:
            traceback.print_exc()
        finally:
            return self.hooks.post_scan(self)

    def scan(self):
        """Start and complete a normal scan."""
        self.scan_mode = "linear"
        return self._scan(self._step_linear)

    def scan_mesh(self):
        """
        Start and complete a mesh scan.

        All combinations of motor positions will be visited.
        """
        self.scan_mode = "mesh"
        return self._scan(self._step_mesh)

    def _test(self, get_points, do_print=True):
        """Base test scan."""
        if do_print:
            print "Starting a test scan."
        self._init_iters()
        data = []
        try: 
            while True:
                pts = get_points()
                data.append(pts)
                for mot, pt in zip(self.mots, pts):
                    if do_print:
                        print "{0}: {1}".format(mot, pt)
        except (StopIteration, GeneratorExit):
            if do_print:
                print "Reached end of test scan."
        except KeyboardInterrupt:
            if do_print:
                print "Test scan interrupted."
        return data

    def test_scan(self, do_print=True):
        """
        Run through a normal test scan.

        Return values from the iterators.
        Print values by default.
        """
        return self._test(self._next_linear, do_print=do_print)

    def test_mesh(self, do_print=True):
        """
        Run through a mesh test scan.

        Return values from the iterators.
        Print values by default.
        """
        return self._test(self._next_mesh, do_print=do_print)

    def get_motors(self):
        """
        Return list of included motor objects.

        The list is a shallow copy. It is safe to mutate the list.
        Changes to the returned motor objects will affect the scan.
        """
        return list(self.mots)

    def get_positions(self):
        """Return list of current motor positions."""
        return self._get_positions(self.mots)

    def _get_positions(self, mots):
        """Generic form of .get_positions"""
        pos = []
        for m in mots:
            if isinstance(m, (tuple, list)):
                pos.append(tuple(self._get_positions(m)))
            else:
                pos.append(m.wm())
        return pos

    def get_iters(self):
        """
        Return list of included iterators.
        
        The list is a deep copy. It is safe to do anything with this
        list or its contents and the scan will be unaffected.
        """
        iters = []
        for i in range(len(self.orig_iters)):
            iter = self._get_iter(i)
            iters.append(iter)
        return iters

    def _get_iter(self, index):
        """Returns a copy of original iterator at index."""
        iter, self.orig_iters[index] = itertools.tee(self.orig_iters[index])
        return iter

    def _process_arg(self, arg):
        """Check arg's type and store it appropriately."""
        if is_motor(arg):
            self.mots.append(arg)
        elif is_iterable(arg):
            self.orig_iters.append(arg)
        elif is_hooks(arg):
            self.hooks = arg
        else:
            print "Skipping invalid argument: {}".format(arg)

    def _init_default_hooks(self):
        """Initialize hooks to default."""
        self._default_hooks = Hooks()
        self.hooks = self._default_hooks

    def _check_args(self):
        """Throw errors on invalid inputs to __init__."""
        if len(self.mots) != len(self.orig_iters):
            raise ValueError(
                "Number of motors must equal number of iterators.")
        if self.hooks == self._default_hooks:
            print "WARNING: No valid hooks object, setting to defaults."

    def _init_iters(self):
        """Make copies of the iterators to allow multiple scans."""
        self.iters = self.get_iters()

    def _step_linear(self):
        """Get the next points and move the motors."""
        pts = self._next_linear()
        self._step(pts)

    def _next_linear(self):
        """Advance all iterators one step. Return the next points."""
        return self._next_linear_iters(self.iters)

    def _next_linear_iters(self, iters):
        """Base of _next_linear without hardcoded self.iters"""
        pts = []
        for iter in iters:
            pts.append(iter.next())
        return pts

    def _step_mesh(self):
        """Get the next mesh points and move the motors."""
        pts = self._next_mesh()
        self._step(pts)

    def _next_mesh(self):
        """
        Advance iterators to next mesh step. Return the next points.

        This method steps through all combinations of iterator
        positions with the fewest total number of motor moves. The first
        motor will move the most times and the last motor will move the
        fewest times (assuming equal number of iterator steps per motor).
        """
        if self._curr_mesh:
            mesh_done = True
            for i in range(len(self.iters)):
                try:
                    self._curr_mesh[i] = self.iters[i].next()
                    mesh_done = False
                    break
                except (StopIteration, GeneratorExit):
                    iter = self._get_iter(i)
                    self._curr_mesh[i] = iter.next()
                    self.iters[i] = iter
            if mesh_done:
                self._curr_mesh = []
                raise StopIteration("No next mesh point. Mesh has been reset.")
        else:
            pts = self._next_linear()
            self._curr_mesh.extend(pts)
        return list(self._curr_mesh)

    def _step(self, pts):
        """Move to the positions in pts and wait."""
        self.hooks.pre_step(self)
        self._move(pts)
        self.wait()
        self.hooks.post_step(self)

    def _move(self, pts):
        """Move the motors to the positions in array pts."""
        self._move_generic(self.mots, pts)

    def _move_generic(self, mots, pts):
        """_move with an arbitrary set of motors."""
        for mot, pt in zip(mots, pts):
            if isinstance(mot, (tuple, list)):
                self._move_generic(mot, pt)
            else:
                mot.mv(pt)

    def wait(self):
        """Wait until all motors are done moving."""
        self._wait_generic(self.mots)

    def _wait_generic(self, mots):
        """_wait with an arbitrary set of motors."""
        for m in mots:
            if isinstance(m, (tuple, list)):
                self._wait_generic(m)
            else:
                m.wait() 

    def to_first_point(self):
        """
        Move all motors to their first point in the scan. May be useful to
        call in pre_scan if you want to move motors to their start positions
        earlier than after the first pre_step.
        """
        iters = self.get_iters()
        pts = []
        for iter in iters:
            pts.append(iter.next())
        self._move(pts)

    @property
    def curr_step(self):
        return self._curr_step

    def print_status(self):
        """Print current scan status."""
        print "Scan step {}".format(self._curr_step)
        mots = self.get_motors()
        for m in mots:
            print "{0}: {1}".format(self._status_name(m), self._status_pos(m))

    def _status_name(self, mot):
        if isinstance(mot, (tuple, list)):
            return "(" + ", ".join([ self._status_name(m) for m in mot ]) + ")"
        else:
            return mot.name

    def _status_pos(self, mot):
        if isinstance(mot, (tuple, list)):
            return "(" + ", ".join([ self._status_pos(m) for m in mot ]) + ")"
        else:
            return str(mot.wm())

    def save_positions(self):
        """Store positions in scan for later use."""
        self._saved = self.get_positions()

    def restore_saved(self):
        """Move motors in scan to last positions from save_positions."""
        self._move(self._saved)
        self.wait()

    def get_stats(self, max_steps=float("inf")):
        """
        Return basic statistics in a dictionary.

        This method is intended to be used to print information about
        a scan before beginning the scan. You can call it in your
        pre_scan hook for this purpose.

        Runs through all iterators, calculating the following stats:
        n_points: array of number of points in each iterator
        iter_maxes: array of greatest position in each iterator
        iter_mins: array of least position in each iterator
        iter_step_avg: array of average step size for each iterator
        scan_maxes: array of greatest position reached in a scan
        scan_mins: array of least position reached in a scan
        scan_step_avg: array of average step size in a scan
            (May differ from iter_maxes/mins/step_avg because scan ends
             if any iterator terminates.)
        scan_points: integer, number of points in scan
        mesh_points: integer, number of points in mesh

        If max_steps is set, stop calculating stats after max_steps in an
        iterator. This may be useful if your iterators run infinitely.
        """
        mots = self.get_motors()
        iters = self.get_iters()
        n_points = []
        iter_maxes = []
        iter_mins = []
        iter_step_avg = []
        for iter in iters:
            count, maxum, minum, step_avg = self._iterator_stats(iter, max_steps)
            n_points.append(count)
            iter_maxes.append(maxum)
            iter_mins.append(minum)
            iter_step_avg.append(step_avg)
        iters = self.get_iters()
        allpts = []
        scan_maxes = []
        scan_mins = []
        scan_step_avg = []
        try:
            while True:
                pts = self._next_linear_iters(iters)
                allpts.append(pts)
        except (StopIteration, GeneratorExit):
            pass
        for i in range(len(iters)):
            ival = (allpts[j][i] for j in range(len(allpts)))
            count, maxum, minum, step_avg = self._iterator_stats(ival, max_steps)
            scan_maxes.append(maxum)
            scan_mins.append(minum)
            scan_step_avg.append(step_avg)
        scan_points = count
        mesh_points = reduce(lambda x, y: x*y, n_points)
        stats = dict()
        for stat in ["n_points", "iter_maxes", "iter_mins", "iter_step_avg",
                     "scan_maxes", "scan_mins", "scan_step_avg", "scan_points",
                     "mesh_points"]:
            stats[stat] = eval(stat)
        return stats

    def _iterator_stats(self, iterator, max_steps):
        """
        Get statistics about an iterator by iterating through it.

        Returns input iterator's number of points, max, min,
        and average step size. Note that this will exhaust the
        iterator. Will loop forever if iterator is infinite, unless
        a maximum step count is chosen. Number of points will return
        as inf if we reached the max number of steps.
        """
        n_points = 0
        maxim = float("-inf")
        minum = float("inf")
        step_sum = 0.0
        prev_val = None
        for val in iterator:
            n_points += 1
            if isinstance(val, tuple):
                maxim = minum = step_sum = float("nan")
            else:
                if val > maxim:
                    maxim = val
                if val < minum:
                    minum = val
                if prev_val != None:
                    step_sum += (val - prev_val)
            prev_val = val
            if n_points >= max_steps:
                break
        if maxim == float("-inf") or minum == float("inf"):
            maxim = float("nan")
            minum = float("nan")
        if n_points <= 1:
            step_avg = 0
        else:
            if math.isnan(step_sum):
                step_avg = float("nan")
            else:
                step_avg = step_sum/(n_points - 1)
        if n_points >= max_steps:
            n_points = float("inf")
        return n_points, maxim, minum, step_avg

    def abort_scan(self, message="Scan aborted."):
        """
        Ends the scan.

        This skips from the current step to the post_scan hook,
        printing message.
        """
        raise AbortScan(message)

class Hooks(object):
    """
    Class to define an interface for the hooks in IterScan.

    It is convenient to define these hooks together in one object because
    they may need to share data. To IterScan, pass in an object that inerits
    from iterscan.Hooks (or at least implements this interface).

    The default hooks simply return motors to their starting positions after
    the scan.
    """
    def pre_scan(self, scan):
        scan.save_positions()

    def post_scan(self, scan):
        scan.restore_saved()

    def pre_step(self, scan):
        pass

    def post_step(self, scan):
        pass

class AbortScan(Exception):
    """Exception raised when we want to end the scan early."""
    pass

def is_motor(obj):
    """Return True if obj is valid motor for scans."""
    if isinstance(obj, (tuple, list)):
        bools = [ is_motor(m) for m in obj ]
        return all(bools)
    else:
        return isinstance(obj, (motor.Motor, vmotor.VirtualMotor))

def is_iterable(obj):
    """Return True if obj is valid iterable for scans."""
    return isinstance(obj, collections.Iterable)

def is_hooks(obj):
    """Return True if obj has valid Hooks for scan."""
    def is_hook(func):
        return len(inspect.getargspec(func)[0]) == 2
    try:
        t1 = is_hook(obj.pre_scan)
        t2 = is_hook(obj.post_scan)
        t3 = is_hook(obj.pre_step)
        t4 = is_hook(obj.post_step)
        return all((t1, t2, t3, t4))
    except:
        return False

#############################################
### Below here are functions for testing ####
#############################################

def _test_motor_factory(name, speed=1):
    import time
    pos = [0]
    moving = False
    def setpos(x):
        pos[0] = x
    def relpos(x):
        pos[0] = pos[0] + x
    def mv(x):
        while wm() != x:
            if wm() > x:
                relpos(-0.001)
            elif wm() < x:
                relpos(0.001)
            if abs(wm() - x) < 0.01:
                setpos(x)
            time.sleep(0.0001/speed)
    def wm():
        return pos[0]
    def wait():
        pass
    return vmotor.VirtualMotor(name, mv, wm , wait)

def _test_test_motor():
    mot1 = _test_motor_factory("mot1", speed=10)
    mot2 = _test_motor_factory("mot2", speed=10)
    mot1.mv(7)
    mot1.wait()
    assert (mot1.wm() == 7), "Test motor did not move to correct location, or wait is broken."
    mot2.mv(-5)
    mot2.wait()
    assert (mot2.wm() == -5), "Test motor did not move to correct location, or wait is broken."
    assert (mot1.wm() == 7), "Motors are inexplicably linked."

def _test_gets():
    tmf = _test_motor_factory
    mots = [tmf("1"), tmf("2")]
    iters = [(x for x in range(5)), (x for x in range(5))]
    scan = IterScan(*(mots + iters))
    assert scan.get_motors() == mots, "IterScan.get_motors() is broken."
    assert scan.get_positions() == [0, 0], "IterScan.get_positions is broken."

def _test_test_scan():
    tmf = _test_motor_factory
    my_scan = IterScan(tmf("1"), tmf("2"), tmf("3"), (x**2 for x in range (10)), (x**0.5 for x in range(10)), (x**3 for x in range(10)))
    data1 = my_scan.test_scan(do_print=False)
    data2 = my_scan.test_scan(do_print=False)
    assert data1 == data2, "Generators give different results after repeated scans."
    simple_scan = IterScan(tmf("simple"), (x for x in range(5)))
    data3 = simple_scan.test_scan(do_print=False)
    assert data3 == [[0], [1], [2], [3], [4]], "Generators return incorrect values."

def _test_test_mesh():
    tmf = _test_motor_factory
    my_scan = IterScan(tmf("1"), tmf("2"), tmf("3"), (x**2 for x in range (10)), (x**0.5 for x in range(10)), (x**3 for x in range(10)))
    data1 = my_scan.test_mesh(do_print=False)
    data2 = my_scan.test_mesh(do_print=False)
    assert data1 == data2, "Generators give different results after repeated mesh scans."
    simple_scan = IterScan(tmf("simple_1"), tmf("simple_2"), tmf("simple_3"), (x for x in range(2)), (x for x in range(3)), (x for x in range(2)))
    data3 = simple_scan.test_mesh(do_print=False)
    correct_data3 = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 2, 0], [1, 2, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1], [0, 2, 1], [1, 2, 1]]
    assert data3 == correct_data3, "Mesh scans return incorrect values.\nExpected: {0}\nReceived: {1}".format(correct_data3, data3)

def _test_real_scan():
    class my_hooks(object):
        n_hook_calls = [0, 0, 0, 0]
        pos_vectors = []
        def pre_scan(self, scan):
            self.n_hook_calls[0] += 1
        def post_scan(self, scan):
            self.n_hook_calls[1] += 1
        def pre_step(self, scan):
            self.n_hook_calls[2] += 1
        def post_step(self, scan):
            self.n_hook_calls[3] += 1
            self.pos_vectors.append(scan.get_positions())
    h = my_hooks()
    tmf = _test_motor_factory
    scan = IterScan(tmf("1", speed=20), tmf("2", speed=20), (x for x in range(5)), (x**2 for x in range(5)), h)
    scan.scan()
    assert h.n_hook_calls[0] == 1, "pre_scan was called {} times instead of 1.".format(h.n_hook_calls[0])
    assert h.n_hook_calls[1] == 1, "post_scan was called {} times instead of 1.".format(h.n_hook_calls[1])
    assert h.n_hook_calls[2] == 5, "pre_step was called {} times instead of 5.".format(h.n_hook_calls[2])
    assert h.n_hook_calls[3] == 5, "post_step was called {} times instead of 5.".format(h.n_hook_calls[3])
    assert h.pos_vectors == [[0, 0], [1, 1], [2, 4], [3, 9], [4, 16]], "Scan steps moved the motors to the wrong positions."
    assert scan.get_positions() == [4, 16], "Scan did not end on correct value."

def _test_real_mesh():
    class my_hooks(object):
        n_hook_calls = [0, 0, 0, 0]
        pos_vectors = []
        def pre_scan(self, scan):
            self.n_hook_calls[0] += 1
        def post_scan(self, scan):
            self.n_hook_calls[1] += 1
        def pre_step(self, scan):
            self.n_hook_calls[2] += 1
        def post_step(self, scan):
            self.n_hook_calls[3] += 1
            self.pos_vectors.append(scan.get_positions())
    h = my_hooks()
    tmf = _test_motor_factory
    scan = IterScan(tmf("1", speed=20), tmf("2", speed=20), (x for x in range(2)), (x**2 for x in range(3)), h)
    scan.scan_mesh()
    assert h.n_hook_calls[0] == 1, "pre_scan was called {} times instead of 1.".format(h.n_hook_calls[0])
    assert h.n_hook_calls[1] == 1, "post_scan was called {} times instead of 1.".format(h.n_hook_calls[1])
    assert h.n_hook_calls[2] == 6, "pre_step was called {} times instead of 6.".format(h.n_hook_calls[2])
    assert h.n_hook_calls[3] == 6, "post_step was called {} times instead of 6.".format(h.n_hook_calls[3])
    assert h.pos_vectors == [[0, 0], [1, 0], [0, 1], [1, 1], [0, 4], [1, 4]], "Scan steps moved the motors to the wrong positions."
    assert scan.get_positions() == [1, 4], "Scan did not end on correct value."

def _test_save_positions():
    tmf = _test_motor_factory
    scan = IterScan(tmf("1", speed=20), tmf("2", speed=20), tmf("3", speed=20), (x for x in [0]), (x for x in [0]), (x for x in [0]))
    scan._move([5, 6, 7])
    scan.wait()
    scan.save_positions()
    assert scan.get_positions() == [5, 6, 7], "Something wrong with move"
    scan._move([0, 0, 0])
    scan.wait()
    scan.restore_saved()
    scan.wait()
    assert scan.get_positions() == [5, 6, 7], "Either save or load is bad"

def _test_get_stats():
    tmf = _test_motor_factory
    scan = IterScan(tmf("1"), tmf("2"), tmf("3"), (x for x in [0, 1]), (x for x in [1, 3, 5]), (x for x in [1, -4, 1]))
    stats = scan.get_stats()
    stats2 = scan.get_stats()
    assert stats == stats2, "Stats returns different results each time."
    keys = ["n_points", "iter_maxes", "iter_mins", "iter_step_avg", "scan_maxes", "scan_mins", "scan_step_avg", "scan_points", "mesh_points"]
    ans = [[2, 3, 3], [1, 5, 1], [0, 1, -4], [1, 2, 0], [1, 3, 1], [0, 1, -4], [1, 2, -5], 2, 18]
    for k, a in zip(keys, ans):
        assert stats[k] == a, "{0} was {1}, expected {2}".format(k, stats[k], a)

def _test_groups():
    class my_hooks(Hooks):
        pos_vectors = []
        def post_step(self, scan):
            self.pos_vectors.append(scan.get_positions())
    h = my_hooks()
    tmf = _test_motor_factory
    scan = IterScan(tmf("1"), (tmf("2"), tmf("3")), (x for x in [0, 1]), (x for x in [(0, 4), (1, 3), (2, 2)]), h)
    tscan = scan.test_scan(do_print=False)
    tmesh = scan.test_mesh(do_print=False)
    scan.scan_mesh()
    assert tscan == [[0, (0, 4)], [1, (1, 3)]], "normal test scans break with groups: {}".format(tscan)
    assert tmesh == [[0, (0, 4)], [1, (0, 4)], [0, (1, 3)], [1, (1, 3)], [0, (2, 2)], [1, (2, 2)]], "mesh test scans break with groups: {}".format(tmesh)
    assert h.pos_vectors == tmesh, "real scans don't give the same values as test scans for mesh: {0} != {1}".format(h.pos_vectors, tmesh)
    stats = scan.get_stats() # output is probably ok, but shouldn't throw an exception

def _test_nested():
    class my_hooks(Hooks):
        pos_vectors = []
        def post_step(self, scan):
            self.pos_vectors.append(scan.get_positions())
    h = my_hooks()
    tmf = _test_motor_factory
    scan = IterScan(tmf("1"), ((tmf("2"), tmf("3")), tmf("4")), [0, 1], [((0, 1), 2), ((4, 3), 6)], h)
    tscan = scan.test_scan(do_print=False)
    tmesh = scan.test_mesh(do_print=False)
    scan.scan_mesh()
    assert tscan == [[0, ((0, 1), 2)], [1, ((4, 3), 6)]], "normal test scans break with nested groups: {}".format(tscan)
    assert tmesh == [[0, ((0, 1), 2)], [1, ((0, 1), 2)], [0, ((4, 3), 6)], [1, ((4, 3), 6)]], "mesh test scans break with nested groups: {}".format(tmesh)
    assert h.pos_vectors == tmesh, "real scans don't give the same values as test scans for mesh: {0} != {1}".format(h.pos_vectors, tmesh)
    stats = scan.get_stats() # check for exceptions

_tests = [_test_test_motor, _test_gets, _test_test_scan, _test_test_mesh, _test_real_scan, _test_real_mesh, _test_save_positions, _test_get_stats, _test_groups, _test_nested]
def _run_tests():
    import traceback
    i = 0
    ok_count = 0
    fail_count = 0
    for test in _tests:
        try:
            i += 1
            print "Running test {}:".format(i)
            test()
            ok_count += 1
        except Exception as exc:
            print 'Test {0} "{1}" failed:'.format(i, test.__name__)
            print traceback.format_exc()
            fail_count += 1
    if fail_count == 0:
        print "All {} tests passed!".format(i)
    else:
        print "{0} tests passed, {1} tests failed.".format(ok_count, fail_count)

if __name__ == "__main__":
    _run_tests()

