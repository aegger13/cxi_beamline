import sys
import collections

class AScan(object):
    def __init__(self, motor, pos1, pos2, num_intervals, return_after=True):
        if isinstance(motor, collections.Sequence):
            self._motor = motor
            self.__init_pos = [ m.wm() for m in motor ]
        else:
            self._motor = [motor]
            self.__init_pos = [motor.wm()]
        if isinstance(pos1, collections.Sequence):
            if len(pos1) != len(self._motor):
              raise ValueError("Number of motors and starting positions are incompatible: %d vs %d" %(len(pos1), len(self._motor)))
            self.__pos1 = pos1
        else:
            self.__pos1 = [pos1] * len(self._motor)
        if isinstance(pos2, collections.Sequence):
            if len(pos2) != len(self._motor):
              raise ValueError("Number of motors and end positions are incompatible: %d vs %d" %(len(pos2), len(self._motor)))
            self.__pos2 = pos2
        else:
            self.__pos2 = [pos2] * len(self._motor)
        self.__num_intervals = num_intervals
        self.__return_after = return_after
        self._delta = [ float(p2 - p1) / num_intervals for p1,p2 in zip(self.__pos1, self.__pos2) ]
        self._nstep = 0
        self.__success = True
        self.__total_steps = num_intervals + 1
        self._pre_scan_hook = self.__no_op
        self._pre_move_hook = self.__no_op
        self._post_move_hook = self.__no_op
        self._post_scan_hook = self.__no_op
        
        self.__validate()

    def __validate(self):       
        ok = True
        for motor, pos1, pos2 in zip(self._motor, self.__pos1, self.__pos2):
            if not motor.within_limits(pos1):
                ok = False
                print "ERROR: motor %s would move outside limits" % (motor.name)
            if not motor.within_limits(pos2):
                ok = False
                print "ERROR: motor %s would move outside limits" % (motor.name)

        if not ok:
            raise Exception("Scan parameters Invalid")

    def __no_op(self, scan):
        pass

    def get_success(self):
        return self.__success

    def get_position(self):
        return [ m.wm() for m in self._motor ]

    def get_initial_position(self):
        return self.__init_pos

    def get_step(self):
        return self._nstep

    def get_delta(self):
        return self.__delta

    def get_total_steps(self):
        return self.__total_steps

    def get_return_after(self):
        return self.__return_after

    # will pass pos1, pos2, nIntervals to this method
    def set_pre_scan_hook(self, hook):
        self._pre_scan_hook = hook
        pass

    # will pass next commanded position to this hook
    def set_pre_move_hook(self, hook):
        self._pre_move_hook = hook
        pass

    # will pass current position to this hook
    def set_post_move_hook(self, hook):
        self._post_move_hook = hook
        pass

    # will pass boolean flag to this hook to tell if scan succeeded
    def set_post_scan_hook(self, hook):
        self._post_scan_hook = hook
        pass

    def get_pos1(self):
        return self.__pos1
        
    def get_pos2(self):
        return self.__pos2

    def get_num_intervals(self):
        return self.__num_intervals

    def _check_limits(self):
        for motor in self._motor:
            lim_status = motor.within_limits()
            if not lim_status:
                raise Exception("Limit violated on '%s'! Scan stopped after %u intervals." % (motor.name, self._nstep))

    def _move(self, positions):
        for motor, pos in zip(self._motor, positions):
            motor.move(pos)

    def _wait(self):
        for motor in self._motor:
            motor.wait()
    
    def go(self):
        hasMoved = False
        self._nstep = 0
        nextpos = self.get_pos1()
        try:

            self._pre_scan_hook(self)

            for step in range(0, self.get_total_steps()):
                self._nstep+=1
                self._pre_move_hook(self)
                self._move(nextpos)
                self._wait()
                self._post_move_hook(self)
                self._check_limits()
                nextpos += self._delta
                nextpos = [ n+d for n,d in zip(nextpos, self._delta) ]

        except Exception, e:
            success = False
            print "ERROR: %s" % e.message
        
        finally:
            if (self.__return_after):
                print "Returning motor(s) to original position..."
                self._move(self.__init_pos)
                self._wait()
                print "Done."
                # TODO: Tell hook if scan succeeded.
            self._post_scan_hook(self)


class DScan(AScan):
    def __init__(self, motor, rel1, rel2, num_intervals, return_after=True):
        if isinstance(motor, collections.Sequence):
            if isinstance(rel1, collections.Sequence):
                if len(rel1) != len(motor):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(rel1), len(motor)))
                pos1 = [ m.wm() + d for m,d in zip(motor, rel1) ]
            else:
                pos1 = [ m.wm() + rel1 for m in motor ]
            if isinstance(rel2, collections.Sequence):
                if len(rel2) != len(motor):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(rel2), len(motor)))
                pos2 = [ m.wm() + d for m,d in zip(motor, rel2) ]
            else:
                pos2 = [ m.wm() + rel2 for m in motor ]
        else:
            pos1 = motor.wm() + rel1
            pos2 = motor.wm() + rel2
        super(DScan, self).__init__(motor, pos1, pos2, num_intervals, return_after)


class A2Scan(AScan):
    def __init__(self,
                 motor1,
                 motor1_pos1,
                 motor1_pos2,
                 motor1_num_intervals,
                 motor2,
                 motor2_pos1,
                 motor2_pos2,
                 motor2_num_intervals,
                 return_after=True
                 ):
        
        
        super(A2Scan, self).__init__(motor1,
                                     motor1_pos1,
                                     motor1_pos2,
                                     motor1_num_intervals,
                                     return_after
                                     )
        
        self.__inner_scan = AScan(motor2,
                                  motor2_pos1,
                                  motor2_pos2,
                                  motor2_num_intervals,
                                  False
                                  )

    def set_pre_move_hook(self, hook):
        self.__inner_scan._pre_move_hook = hook
        pass

    def set_pre_outer_move_hook(self, hook):
        self._pre_move_hook = hook
        pass

    def set_post_move_hook(self, hook):
        self.__inner_scan._post_move_hook = hook
        pass

    def set_post_outer_move_hook(self, hook):
        self._post_move_hook = hook
        pass
    
    def go(self):
        hasMoved = False
        self._nstep = 0
        nextpos = self.get_pos1()
        try:

            self._pre_scan_hook(self)

            for step in range(0, self.get_total_steps()):
                self._nstep+=1
                self._pre_move_hook(self)
                self._move(nextpos)
                self.__inner_scan._move(self.__inner_scan.get_pos1())
                self.__inner_scan._wait()
                self._wait()
                self.__inner_scan.go()
                self._post_move_hook(self)
                self._check_limits()
                nextpos = [ n+d for n,d in zip(nextpos, self._delta) ]

        except Exception, e:
            success = False
            print "ERROR: %s" % e
            raise e
                    
        finally:
            if (self.get_return_after()):
                print "Returning motors to original position"
                sys.stdout.flush()
                self._move(self.get_initial_position())
                self.__inner_scan._move(self.__inner_scan.get_initial_position())
                self.__inner_scan._wait()
                self._wait()
            self._post_scan_hook(self)


# This D2Scan class doesn't work well at all.  It gets really messed up and screws up other things.
class D2Scan(A2Scan):
    def __init__(self,
                 motor1,
                 motor1_rel1,
                 motor1_rel2,
                 motor1_num_intervals,
                 motor2,
                 motor2_rel1,
                 motor2_rel2,
                 motor2_num_intervals,
                 return_after=True
                 ):

        if isinstance(motor1, collections.Sequence):
            if isinstance(motor1_rel1, collections.Sequence):
                if len(motor1_rel1) != len(motor1):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(motor1_rel1), len(motor1)))
                motor1_pos1 = [ m.wm() + d for m,d in zip(motor1, motor1_rel1) ]
            else:
                motor1_pos1 = [ m.wm() + motor1_rel1 for m in motor1 ]
            if isinstance(motor1_rel2, collections.Sequence):
                if len(motor1_rel2) != len(motor1):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(motor1_rel2), len(motor1)))
                motor1_pos2 = [ m.wm() + d for m,d in zip(motor1, motor1_rel2) ]
            else:
                motor1_pos2 = [ m.wm() + motor1_rel2 for m in motor1 ]
        else:
            motor1_pos1 = motor1.wm() + motor1_rel1
            motor1_pos2 = motor1.wm() + motor1_rel2

        if isinstance(motor2, collections.Sequence):
            if isinstance(motor2_rel1, collections.Sequence):
                if len(motor2_rel1) != len(motor2):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(motor2_rel1), len(motor2)))
                motor2_pos1 = [ m.wm() + d for m,d in zip(motor2, motor2_rel1) ]
            else:
                motor2_pos1 = [ m.wm() + motor2_rel1 for m in motor2 ]
            if isinstance(motor2_rel2, collections.Sequence):
                if len(motor2_rel2) != len(motor2):
                    raise ValueError("Number of motors and relative starting positions are incompatible: %d vs %d" %(len(motor2_rel2), len(motor2)))
                motor2_pos2 = [ m.wm() + d for m,d in zip(motor2, motor2_rel2) ]
            else:
                motor2_pos2 = [ m.wm() + motor2_rel2 for m in motor2 ]
        else:
            motor2_pos1 = motor2.wm() + motor2_rel1
            motor2_pos2 = motor2.wm() + motor2_rel2
        
        super(D2Scan, self).__init__(motor1, motor1_pos1, motor1_pos2, motor1_num_intervals, motor2, motor2_pos1, motor2_pos2, motor2_num_intervals, return_after=True)
