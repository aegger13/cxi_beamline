"""
Module to view and change parameters from the lcls event/timing system screen.
"""
from psp.Pv import Pv
import subprocess

ioc_base = "IOC:IN20:EV01:" 
event_base = "EVNT:SYS0:1:"
trigger_base = "PATT:SYS0:1:"

class LclsEvent(object):
    """
    Contains methods to view and change parameters from the lcls
    event/timing system screen.
    """
    def __init__(self):
        self._bykik_abort_pv = Pv(ioc_base + "BYKIK_ABTACT")
        self._bykik_period_pv = Pv(ioc_base + "BYKIK_ABTPRD")

    def edm_screen(self):
        """
        Open up the lcls event/timing screen.
        """
        subprocess.Popen(["sh", "/reg/g/pcds/package/epics/3.14-dev/screens/edm/common/current/lcls/lclsSystemArea.sh"])

    def bykik_status(self):
        """
        Return status of bykik abort (Disable or Enable)
        """
        val = self._bykik_abort_pv.get()
        if val == 0:
            return "Disable"
        else:
            return "Enable"

    def bykik_disable(self):
        """
        Disable bykik abort
        """
        self._bykik_abort_pv.put(0)

    def bykik_enable(self):
        """
        Enable bykik abort
        """
        self._bykik_abort_pv.put(1)

    def bykik_get_period(self):
        """
        Get number of events between bykik aborts
        """
        return self._bykik_period_pv.get()

    def bykik_set_period(self, period):
        """
        Set number of events between bykik aborts
        """
        self._bykik_period_pv.put(period)

