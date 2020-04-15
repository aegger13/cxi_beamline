from daq_config_device import Dcfg, SubcfgDict, SubcfgList
import math

class Acqiris(Dcfg):
    """
    Class for the Acqiris digitizers. Provides a way to adjust Acqiris
    configurations from within a hutch python session.
    """
    def __init__(self, hutch, *aliases):
        """
        Programatically sets up get_name and set_name methods during init.
        """
        Dcfg.__init__(self, hutch, *aliases, typeid=0x10004)
        self._add_methods("sample_num", "horiz", "nbrSamples")
        self._add_methods("sample_interval", "horiz", "sampInterval")
        self._add_methods("delay_time", "horiz", "delayTime")
        self._add_methods("channel_num", "nbrChannels")
        self._add_methods("channel_mask", "channelMask")
        self._add_methods("conv_per_ch", "nbrConvertersPerChannel")
        
        self.trig = SubcfgDict(self, "trig")
        self.trig._add_methods("coupling", "coupling")
        self.trig._add_methods("input", "input")
        self.trig._add_methods("level", "level")
        self.trig._add_methods("slope", "slope")
        self._add_subcfg(self.trig, "trig")

        self.vert = SubcfgList(self, "vert")
        self.vert._add_methods("bandwidth", "bandwidth")
        self.vert._add_methods("coupling", "coupling")
        self.vert._add_methods("full_scale", "fullScale")
        self.vert._add_methods("offset", "offset")
        self.vert._add_methods("slope", "slope")
        self._add_subcfg(self.vert, "vert")

    def commit(self):
        """
        Commits all changes to the database using the current stored config
        dictionary. Does a sanity check before the commit.
        """
        if self._sanity_check():
            Dcfg.commit(self)

    def _sanity_check(self):
        """
        Checks the configuration, displaying warnings as needed.
        Returns True if it's ok to commit.
        """
        rate = self._best_case_rate(self.get_delay_time(), self.get_sample_num(), self.get_sample_interval())
        if rate < 120:
            print "Warning: this configuration may error above {0} Hz".format(rate)
        return True

    def _best_case_rate(self, delay, samples, interval):
        """
        Estimates the highest rate for which we know this configuration will
        not cause errors. These errors occur if the time spent for each
        trigger is greater than the time between triggers.
        """
        base = (delay + samples * interval) * 0.9
        return int(math.floor(1/base))

'''
Example dictionary for Acqiris:

{'channelMask': 15L,
 'horiz': {'delayTime': 0.0,
  'nbrSamples': 1000L,
  'nbrSegments': 1L,
  'sampInterval': 5e-10},
 'nbrBanks': 1L,
 'nbrChannels': 4L,
 'nbrConvertersPerChannel': 1L,
 'trig': {'coupling': 0L, 'input': -1L, 'level': 0.5, 'slope': 0L},
 'vert': [{'bandwidth': 0L,
   'coupling': 3L,
   'fullScale': 2.0,
   'offset': 0.0,
   'slope': 3.0517578125e-05},
  {'bandwidth': 0L,
   'coupling': 3L,
   'fullScale': 5.0,
   'offset': -2.0,
   'slope': 7.62939453125e-05},
  {'bandwidth': 0L,
   'coupling': 3L,
   'fullScale': 5.0,
   'offset': -2.0,
   'slope': 7.62939453125e-05},
  {'bandwidth': 0L,
   'coupling': 3L,
   'fullScale': 2.0,
   'offset': 0.0,
   'slope': 3.0517578125e-05},
  {'bandwidth': 48L,
   'coupling': 1301629496L,
   'fullScale': -5.846875297802483e+307,
   'offset': 1.42157e-318,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 0L,
   'coupling': 0L,
   'fullScale': 1.02498888384e-312,
   'offset': 0.0,
   'slope': 1.564009e-317},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -5.846875297802483e+307,
   'offset': -5.846875297802483e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4282531902L,
   'coupling': 4279637268L,
   'fullScale': -5.846875297802483e+307,
   'offset': -4.718911045120785e+307,
   'slope': -8.921623684390995e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -2.0873877001746789e+307,
   'offset': -5.846875297802483e+307,
   'slope': -3.185100860862242e+302},
  {'bandwidth': 4284637277L,
   'coupling': 4282334780L,
   'fullScale': -1.2768665779352846e+305,
   'offset': -3.7606008942831205e+307,
   'slope': -1.9483437773670724e+300},
  {'bandwidth': 4283255881L,
   'coupling': 4292137160L,
   'fullScale': -1.382411114889729e+307,
   'offset': -5.846875284015723e+307,
   'slope': -2.109391959975783e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4284637277L,
   'fullScale': -3.6196053584306446e+307,
   'offset': -8.570181157286843e+304,
   'slope': -5.523079465378791e+302},
  {'bandwidth': 4289110941L,
   'coupling': 4291939781L,
   'fullScale': -1.1116374410898811e+305,
   'offset': -3.478607683729734e+307,
   'slope': -1.6962241227567766e+300},
  {'bandwidth': 4292137160L,
   'coupling': 4292137160L,
   'fullScale': -1.382411114889729e+307,
   'offset': -5.846875284278346e+307,
   'slope': -2.109391959975783e+302},
  {'bandwidth': 4292137160L,
   'coupling': 4278321666L,
   'fullScale': -5.846875297802483e+307,
   'offset': -1.382411114889729e+307,
   'slope': -8.921623684390995e+302}]}
'''
