from daq_config_device import Dcfg
import subprocess
import copy

class Cspad2x2(Dcfg):
    """
    DAQ configuration object for the Cspad2x2
    """
    def __init__(self, daq, cspadID, hutch, src, *aliases):
        Dcfg.__init__(self, hutch, *aliases, typeid=0x2002b, src=src)
        self.daq = daq
        self._id = cspadID
        self._run = None
        self._add_methods("inactive_run_mode", "inactiveRunMode")
        self._add_options("inactive_run_mode", "No running", "Run but drop",
                          "Run and send to server", "Run and send triggered by TTL",
                          "External trigger send to server", "External trigger drop.")
        self._add_methods("active_run_mode", "activeRunMode")
        self._add_options("active_run_mode", "No running", "Run but drop",
                          "Run and send to server", "Run and send triggered by TTL",
                          "External trigger send to server", "External trigger drop.")
        self._add_methods("run_trig_delay", "runTriggerDelay")
        self._add_methods("test_data_index", "tdi")
        self._add_methods("acd_threshold", "protectionSystem", "adcThreshold")
        self._add_methods("pixel_count_threshold", "protectionSystem", "pixelCountThreshold")
        self._add_methods("bad_asic_mask", "badAsicMask")
        self._add_methods("sector_mask", "roiMask")
        # Special keys:
        # gain, pots, shiftTest, version

    def _xtc_dot_get_line(self, xtc):
        """Override a single line in main module... To fix weird bug."""
        return xtc.get(0)

    def take_pedestal(self):
        """ Automates the pedestal-taking process. """
        self.daq.wait()
        partition = self.daq.getPartition()
        is_in_partition = self._cspad_only(partition)
        if not is_in_partition:
            print "WARNING: cspad not in partition. Aborting..."
            return
        print "Beginning daq recording run for pedestal..."
        self.daq.begin(events=1000)
        self.daq.wait()
        self._run = self.daq.runnumber()
        print "Done, running bash script..."
        p = self.bash_makepeds(self._run)
        self.daq.configure(partition=partition)
        self.daq.wait()
        p.wait()
        print "Done."

    def bash_makepeds(self, run=None):
        """
        Starts the hutch's makepeds bash script. Uses input run, or defaults
        to the last run from a call to self.take_pedestal().
        """
        if run is None:
            if self._run is None:
                print "Please choose a run!"
                return
            run = self._run
        bashCommand = "/reg/neh/home/{0}opr/bin/{0}makepeds".format(self.hutch.lower())
        options = " -r {0}".format(run)
        process = subprocess.Popen(bashCommand + options)
        return process

    def _cspad_only(self, part):
        """
        Adjusts the partition so that only the cspad is recording. Returns
        True if successful, False otherwise.
        """
        partition = copy.deepcopy(part)
        nodes = partition["nodes"]
        foundCspad = False
        for node in nodes:
            id = node["id"]
            if id == self._id:
                foundCspad = True
                node["record"] = True
            else:
                node["record"] = False
        if foundCspad:
            daq.configure(partition=partition)
        return foundCspad

    def _load(self):
        """
        Overrides the standard load function to "poke" the dictionary...
        I do this because of the weird error mentioned in __init__.
        """
        Dcfg._load(self)
        try:
            for key in self._dcurr:
                pass
        except:
            pass

'''
{'activeRunMode': 3L,
 'asicMask': 1L,
 'badAsicMask': 0L,
 'concentratorVersion': 0L,
 'inactiveRunMode': 1L,
 'payloadSize': 287156L,
 'protectionEnable': 1L,
 'protectionSystem': {'adcThreshold': 67L, 'pixelCountThreshold': 1200L},
 'quad': {'PeltierEnable': 0L,
  'acqDelay': 280L,
  'ampIdle': 3598L,
  'ampReset': 0L,
  'biasTuning': 12594L,
  'dataMode': 0L,
  'digCount': 16383L,
  'digDelay': 960L,
  'digPeriod': 25L,
  'edgeSelect': 1L,
  'gain': [[GIGANTIC 2D ARRAY]],
  'humidThold': 0L,
  'injTotal': 0L,
  'intTime': 5000L,
  'kdConstant': 0L,
  'kiConstant': 0L,
  'kpConstant': 0L,
  'pots': [LONG LIST],
  'prstSel': 0L,
  'readClkHold': 1L,
  'readClkSet': 1L,
  'rowColShiftPer': 3L,
  'setPoint': 2315L,
  'shiftSelect': 3L,
  'shiftTest': 4294967295L,
  'version': 4294967295L},
 'roiMask': 3L,
 'runTriggerDelay': 12750L,
 'tdi': 4L}
'''
