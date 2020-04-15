"""
Object that connects to the pmgr command-line interface.
See the pmgr code at /reg/g/pcds/pyps/apps/pmgr or check confluence
for more details
"""
import functools
import pmgr.pmgrUtils as base
import pmgr.utilsPlus as plus
import psp.Pv
import pyca
from blutil.threadtools import PycaThread, thread_with_timeout
from blutil.doctools import doc_inherit

"""
Only one process can acquire a mySQL write lock at a time, so a timeout is
introduced here to prevent blocking the interactive interpreter indefinitely
in a worst-case lock out situation.
"""
thread_with_timeout = functools.partial(thread_with_timeout, timeout=40,
    err_msg="WARNING: Database transaction timed out!", ThreadClass=PycaThread)

class Pmgr(object):
    """
    Object to connect to a parameter manager mySQL database.
    Assumes the database is set up with one object per unique SN.
    """
    def __init__(self, hutch, pmgr_type):
        """
        hutch (string): the 3-letter hutch name (e.g. xpp)
        pmgr_type (string): which parameter manager (e.g. ims_motor)
        """
        self._hutch = hutch
        self._pmgr_type = pmgr_type

    def _load_pmgr(self):
        """
        Connect to parameter manager by creating a pmgrobj
        """
        return plus.getPmgr(self._pmgr_type, self._hutch, False)

    def _get_SN(self, PV):
        """
        Retrieve the serial number in the default way (.SN PV)
        """
        return psp.Pv.get(PV + ".SN")

# Disable save_config for now because it overwrites old configs. This is
# dangerous because more than one motor can share a config. We either need a
# rollback API or pmgrUtils.saveConfig needs to not overwrite configs.
#    def save_config(self, PV):
#        """
#        Save current parameters as a new configuration. Set the config
#        field in the parameter manager to this new configuration.
#        """
#        return thread_with_timeout(base.saveConfig, (PV, self._hutch,
#            self._load_pmgr(), self._get_SN(PV), False, False,))

    def _is_auto(self, PV):
        """
        Return True if the PV is autoconfigurable (unique serial number)
        """
        return plus.checkCanAuto(self._load_pmgr(), PV)

    def apply_config(self, PV, dumb_config=None, dumb_confirm=True,
                     name=None):
        """
        If the device is autoconfigurable, autoconfigure it.
        Otherwise, apply dumb_config or prompt user to choose a config.
        """
        if self._is_auto(PV):
            return thread_with_timeout(base.applyConfig, (PV, [self._hutch],
                self._pmgr_type, self._get_SN(PV), False, False,),
                dict(name=name))
        else:
            return thread_with_timeout(base.applyConfig, (PV, [self._hutch],
                self._pmgr_type, self._get_SN(PV), False, False,),
                dict(dumb=True, dumb_cfg=dumb_config,
                     dumb_confirm=dumb_confirm, name=name))

    def diff(self, PV):
        """
        Show differences between object's autoconfig (or saved config) and
        the live configuration.
        """
        return base.Diff(PV, self._hutch, self._load_pmgr(),
            self._get_SN(PV), False)
        
class MotorPmgr(Pmgr):
    """
    Object to connect to an ims_motor parameter manager mySQL database.
    Assumes the database is set up with one motor per unique controller SN.
    """
    def __init__(self, hutch):
        """
        hutch (string): the 3-letter hutch name (e.g. xpp)
        """
        Pmgr.__init__(self, hutch, "ims_motor")

    def _motor_to_pv(self, motor):
        """
        Extract pv name from motor object or echo back string
        """
        if not isinstance(motor, basestring):
            return motor.pvname
        return motor

    def _get_SN(self, motor):
        """
        Get the serial number of input PV or motor object.
        """
        return Pmgr._get_SN(self, self._motor_to_pv(motor))

#    @doc_inherit
#    def save_config(self, motor):
#        return Pmgr.save_config(self, self._motor_to_pv(motor))

    def _is_auto(self, PV):
        """
        Override base _is_auto to use motor-specific method.
        """ 
        return not plus.dumbMotorCheck(PV)

    @doc_inherit
    def apply_config(self, motor, dumb_config=None, dumb_confirm=True):
        return Pmgr.apply_config(self, self._motor_to_pv(motor),
                                 dumb_config=dumb_config,
                                 dumb_confirm=dumb_confirm,
                                 name=motor.name)

    @doc_inherit
    def diff(self, motor):
        return Pmgr.diff(self, self._motor_to_pv(motor))


class MotorPmgrSinglet(MotorPmgr):
    """
    Object to connect to the ims_motor parameter manager for a specific motor.
    Assumes the database has a unique entry for this motor's controller's SN.
    """
    def __init__(self, hutch, motor):
        """
        hutch (string): the 3-letter hutch name (e.g. xpp)
        motor (Motor, string): the Motor object or PV of this motor.
        """
        self._motor = motor
        MotorPmgr.__init__(self, hutch)

#    @doc_inherit
#    def save_config(self):
#        MotorPmgr.save_config(self, self._motor)

    @doc_inherit
    def apply_config(self, dumb_config=None, dumb_confirm=True):
        MotorPmgr.apply_config(self, self._motor, dumb_config=dumb_config,
                               dumb_confirm=dumb_confirm)
        self.diff()

    @doc_inherit
    def diff(self):
        MotorPmgr.diff(self, self._motor)

