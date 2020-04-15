"""
Module to configure channel daq name, scale, and offset for usb encoder
channels
"""
from daq_config_device import Dcfg, SubcfgDict

class UsbEncoder(Dcfg):
    def __init__(self, hutch, *aliases):
        Dcfg.__init__(self, hutch, *aliases, typeid=0x10065)
        for i in range(4):
            ch = Channel(self, i)
            istring = "ch{}".format(i)
            self._add_subcfg(ch, istring)
            setattr(self, istring, ch)

class Channel(SubcfgDict):
    def __init__(self, parent, n_channel):
        SubcfgDict.__init__(self, parent, "chan{}".format(n_channel))
        self._add_methods("scale", "scale")
        self._add_methods("offset", "offset")
        self._add_methods("name", "name")

