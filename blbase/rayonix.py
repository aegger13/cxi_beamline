from daq_config_device import Dcfg

class Rayonix(Dcfg):
    """
    Class for managing the Rayonix detector. Can adjust Rayonix configuration
    in the DAQ and take pedestal runs.
    """
    #def __init__(self, daq, rayonixID, hutch, *aliases):
    def __init__(self, hutch, *aliases):
        Dcfg.__init__(self, hutch, *aliases, typeid=0x20049)
        #self.daq = daq # Pass in the main daq instance (at most 1 can be active)
        #self._rayonixID = rayonixID
        self._add_methods("readout_mode", "readoutMode")
        self._add_options("readout_mode", "Standard", "High gain", "High noise", "HDR")
        self._add_methods("_binning_f", "binning_f")
        self._add_methods("_binning_s", "binning_s")
        self._register("binning", "binning_f")
        self._add_methods("trigger_mode", "trigger")
        self._add_options("trigger_mode", "Frame transfer", "Bulb mode")
        self._add_methods("pedestal_mode", "darkFlag")
        self._add_options("pedestal_mode", "Keep Current Background", "Update background on config")
        #self._add_methods("_pedestal", "darkFlag")

    def get_binning(self, live=False):
        """
        Get the binning value in the Rayonix configuration as a string.
        """
        val = self._get_binning_f(live)
        return "{0}x{0} (Resolution {1}x{1})".format(val, int(3840/val))

    def set_binning(self, val, commit=False):
        """
        Set the binning value in the Rayonix configuration.

        Input is an integer among 2, 3, 4, 5, 6, 8, 10 to get a binning
        value of 2x2, 3x3, 4x4, etc.
        """
        valid = (2, 3, 4, 5, 6, 8, 10)
        if val not in valid:
            print "{0}x{0} is an invalid binning.".format(val)
            print "Valid inputs are {0}".format(valid)
            return
        self._set_binning_f(val, False)
        self._set_binning_s(val, False)
        if commit:
            self.commit()

#    def take_pedestal(self):
#        """ Automates the pedestal routine for the Rayonix. """
#        if self._has_changes():
#            print "There are uncommitted changes to the Rayonix configuration."
#            print "This must be resolved before taking the pedestal:"
#            self.diff()
#            i = raw_input("y : commit changes\nn : discard changes\nx : abort pedestal")
#            if i.lower() == "y":
#                self.commit()
#            elif i.lower() == "n":
#                self.cancel_set()
#            else:
#                "Aborting pedestal..."
#                return
#        self.daq.wait()
#        self.daq.connect()
#        if not self.is_in_partition():
#            print "WARNING: Rayonix not in daq partition! Aborting pedestal!"
#            return
#        print "Disabling recording and starting pedestal..."
#        orig_record = self.daq_record
#        self.daq.record = False
#        self._enable_pedestal()
#        self.daq.configure()
#        self.daq.begin(events=10)
#        self.daq.wait()
#        self._disable_pedestal()
#        self.daq.record = orig_record
#        print "take_pedestal routine done."

#    def is_in_partition(self):
#        """ Returns True if Rayonix is in the DAQ partition. """
#        part = self.daq.getPartition()
#        nodes = part["nodes"]
#        for node in nodes:
#            id = node["id"]
#            if id == self._rayonixID:
#                return True
#        return False

#    def _enable_pedestal(self):
#        self._set_pedestal(1, commit=True)

#    def _disable_pedestal(self):
#        self._set_pedestal(0, commit=True)

