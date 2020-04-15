# Python class to interface with the Vitara Laser Timetool Drift Control.
# Mimics features of the edm screen.

# Use this interface so we can adapt to new python easily
import psp.Pv
def caget(pv):
    return psp.Pv.get(pv)
def caput(pv, value):
    return psp.Pv.put(pv, value)

class Vitara(object):
    def __init__(self, pvbase, ipmpv):
        self._pv = pvbase
        self._ipm = ipmpv

    def status(self):
        print "Timetool Drift Control:"
        print "Accumulation: {0}, Correction: {1}".format(self.accumulation(), self.correction())
        print "Current Correction: {0} ns".format(self.current_correction())
        print "  IPM: {0:.6f}, low: {1}, high: {2}".format(self.ipm(), self.ipm_low(), self.ipm_high())
        print "TTAMP: {0:.6f}, low: {1}, high: {2}".format(self.tt_amp(), self.tt_amp_low(), self.tt_amp_high())
        print "Noise Anti-Eliminator: {0} V".format(self.noise_anti_eliminator())

    def accumulation(self, state=None):
        """ Gets or sets accumulation state ("ON" or "OFF") """
        return self._onoff_enum(self._pv + ":TT_DRIFT_ACCU_ENABLE", state)

    def correction(self, state=None):
        """ Gets or sets correction state ("ON" or "OFF") """
        return self._onoff_enum(self._pv + ":TT_DRIFT_ENABLE", state)

    def current_correction(self):
        """ Returns the current correction in ns. """
        return caget(self._pv + ":matlab:04")

    def zero(self):
        """ Toggles the zero button """
        return self._toggle(self._pv + ":TT_DRIFT_RESET")

    def make_explicit(self):
        """ Toggles the make explicit button """
        return self._toggle(self._pv + ":TT_DRIFT_MAKEEXP")

    def ipm(self):
        """ Returns the ipm value associated with the Vitara. """
        return caget(self._ipm)

    def ipm_high(self, value=None):
        """ Get or set the ipm high value for alarm purposes. """
        return self._get_or_set(self._pv + ":matlab:28.HIGH", value)

    def ipm_low(self, value=None):
        """ Get or set the ipm low value for alarm purposes. """
        return self._get_or_set(self._pv + ":matlab:28.LOW", value)

    def tt_amp(self, value=None):
        """ Get the timetool amplitude. """
        return caget(self._pv + ":matlab:23")

    def tt_amp_high(self, value=None):
        """ Get or set the timetool high value for alarm purposes. """
        return self._get_or_set(self._pv + ":matlab:23.HIGH", value)

    def tt_amp_low(self, value=None):
        """ Get or set the ipm low value for alarm purposes. """
        return self._get_or_set(self._pv + ":matlab:23.LOW", value)

    def noise_anti_eliminator(self, value=None):
        """ Get or set the noise anti-eliminator voltage. """
        return self._get_or_set(self._pv + ":CH1_FEEDBACK_GAIN.VAL", value)

    def _get_or_set(self, pv, value):
        if value is None:
            return caget(pv)
        else:
            return caput(pv, value)

    def _onoff_enum(self, pv, state):
        if type(state) == str:
            state = state.upper()
        elif state == 1:
            state = "ON"
        elif state == 0:
            state = "OFF"
        val = self._get_or_set(pv, state)
        if val == 1:
            return "ON"
        elif val == 0:
            return "OFF"
        else:
            return val

    def _toggle(self, pv):
        val = caget(pv)
        if val == 1:
            caput(pv, 0)
            print "Toggled off"
        elif val == 0:
            caput(pv, 1)
            print "Toggled on"
        else:
            print "Some python bug involving _toggle method"

