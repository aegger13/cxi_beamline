"""
Module to change the daq evr configurations on the fly.

Classes:
Evr: Main object, allows changing the configurations
Output: Secondary object to visualize which ports use which pulses
"""

from daq_config_device import Dcfg, SubcfgList, print_table

# Magic number unique to evr configurations

class Evr(Dcfg):
    """
    Class to view and edit the daq evr configurations.
    """
    def __init__(self, hutch, *aliases):
        """
        Hutch is a string representing the 3-letter hutch abbreviation
        associated with this daq evr.

        Aliases are strings and are all of the profiles to view and change.
        These profiles will be synced.
        """
        Dcfg.__init__(self, hutch, *aliases, typeid=0x0008)

        self.pulses = SubcfgList(self, "pulses")
        self.pulses._add_methods("polarity", "polarity")
        self.pulses._add_methods("delay", "delay")
        self.pulses._add_methods("width", "width")
        self._add_subcfg(self.pulses, "Pulses")

        self.eventcodes = SubcfgList(self, "eventcodes")
        self.eventcodes._add_methods("code", "code")
        self.eventcodes._add_methods("type", "type")
        self.eventcodes._add_methods("desc", "desc")
        self._add_subcfg(self.eventcodes, "Event Codes")

        outputs = self.cfg_dict_get()["outputs"]
        modules = {d["module"] for d in outputs}
        for evr_num in modules:
            setattr(self, "evr{}".format(evr_num), Output(self, evr_num))

class Output(object):
    def __init__(self, evr, module):
        self._evr = evr
        self._module = module

    def show_all(self):
        """
        Print all daq evr connections
        """
        outputs = self._evr.cfg_dict_get()["outputs"]
        data = [["Polarity"], ["Delay"], ["Width"]]
        colls = 13
        for i in range(colls):
            data.append([i])
        curr_out = 0
        first_pulse = None
        for pulse in range(self._evr.pulses.count()):
            try:
                while outputs[curr_out]["module"] != self._module:
                    curr_out += 1
            except IndexError:
                break
            if outputs[curr_out]["pulse"] <= pulse:
                for coll in range(colls):
                    try:
                        d = outputs[curr_out]
                    except IndexError:
                        d = dict(conn=None, pulse=None)
                    if d["conn"] == coll and d["pulse"] == pulse:
                        data[coll + 3].append("[X]")
                        if first_pulse is None:
                            first_pulse = pulse
                        curr_out += 1
                    else:
                        data[coll + 3].append("[_]")
        i = first_pulse
        while len(data[0]) < len(data[3]):
            data[0].append(self._evr.pulses.get_polarity(i))
            data[1].append(self._evr.pulses.get_delay(i))
            data[2].append(self._evr.pulses.get_width(i))
            i += 1
        print_table(data)


"""
Structure of the cfg_dict:
        #Same order as pulses tab, but no indication where evr0 stops and evr1 starts (though 1 always after 0)
dict = {"pulses"     : list(n x {"delay"    : float(s),
                                 "polarity" : "Pos" or "Neg",
                                 "pulse"    : list index, 
                                 "width"    : float(s)}),
        #Same order as eventcodes tab, but no indication when global codes start (though always after other codes)
        "eventcodes" : list(m x {"code"         : long, # The event code
                                 "desc"         : string, # Description field (all of these look blank)
                                 "maskClear"    : long, # 0L or 1L, no idea (all look like 0)
                                 "maskSet"      : long, # 0L or 1L, no idea (all look like 0)
                                 "maskTrigger"  : long, # 0L or 1L, no idea (all look like 0)
                                 "readoutGroup" : long, # 1L if type is "readout", 0L otherwise
                                 "releaseCord"  : long, # 0L or 1L, no idea (all look like 1)
                                 "reportDelay"  : long, # 0L or 1L, no idea (all look like 0)
                                 "reportWidth"  : long, # 0L or 1L, no idea (all look like 1)
                                 "type"         : string}), # e.g. readout, command
        # Corresponds to the checkbox diagram. Sorted by module, pulse, conn in that order.
        "outputs"    : list(p x {"conn"   : long, # Port connected
                                 "module" : long, # Which EVR
                                 "pulse"  : long})} # Which Pulse
"""
