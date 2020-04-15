from daq_config_device import Dcfg, SubcfgList, SubcfgDict
from blutil.calc import TTfactor, TTgetThicknessAtFactor

class Timetool(object):
    """
    Timetool object. Used to group useful timetool functions.
    """
    def __init__(self, hutch, aliases, src=None, **motors):
        """
        hutch: 3-letter string, e.g. "xpp"
        aliases: daq config profiles in a list, e.g. ["BEAM", "BEAM_PP"]
        src: unique camera id to be used for config if multiple timetools
        motors: motors to include in this object
        """
        if isinstance(aliases, basestring):
            aliases = (aliases,)
        try:
            self.config = TimetoolConfig(hutch, *aliases, src=src)
        except Exception, exc:
            print "skipping timetool daq config, bad args or out of date pycdb"
            print exc
        for name, mot in motors.items():
            setattr(self, name, mot)
        self.TTfactor = TTfactor
        self.TTgetThicknessAtFactor = TTgetThicknessAtFactor


class TimetoolConfig(Dcfg):
    """
    Class for the Timetool daq configuration.
    """
    def __init__(self, hutch, *aliases, **src_arg):
        """
        Programatically sets up get_name and set_name methods during init.
        """
        src = src_arg.get("src", None)
        Dcfg.__init__(self, hutch, *aliases, typeid=0x20056, src=src)

        self.beam_logic = SubcfgList(self, "beam_logic")
        self.beam_logic._add_methods("event_code", "event_code")
        self.beam_logic._add_methods("logic_op", "logic_op")
        self.beam_logic._add_enum("logic_op", "EventLogic")
        self._add_subcfg(self.beam_logic, "beam_logic")

        self.laser_logic = SubcfgList(self, "laser_logic")
        self.laser_logic._add_methods("event_code", "event_code")
        self.laser_logic._add_methods("logic_op", "logic_op")
        self.laser_logic._add_enum("logic_op", "EventLogic")
        self._add_subcfg(self.laser_logic, "laser_logic")

        for pre in ["ref", "sb", "sig"]:
            if pre != "sig":
                conv = "{}_convergence".format(pre)
                self._add_methods(conv, conv)
            for suf in ["hi", "lo"]:
                roi = "{0}_roi_{1}".format(pre, suf)
                setattr(self, roi, SubcfgDict(self, roi))
                getattr(self, roi)._add_methods("column", "column")
                getattr(self, roi)._add_methods("row", "row")
                self._add_subcfg(getattr(self, roi), roi)
        self._add_methods("reference_projection_size", "reference_projection_size")
        self._add_methods("sideband_projection_size", "sideband_projection_size")
        self._add_methods("signal_projection_size", "signal_projection_size")
        self._add_methods("signal_cut", "signal_cut")

        self._add_methods("project_axis", "project_axis")
        self._add_enum("project_axis", "Axis")
        self._add_methods("calib_poly", "calib_poly")
#        self._add_methods("weights", "weights")

        self._add_methods("subtract_sideband", "subtract_sideband")
        self._add_options("subtract_sideband", "No", "Yes")
        self._add_methods("use_reference_roi", "use_reference_roi")
        self._add_options("use_reference_roi", "No", "Yes")
        self._add_methods("write_image", "write_image")
        self._add_options("write_image", "No", "Yes")
        self._add_methods("write_projections", "write_projections")
        self._add_options("write_projections", "No", "Yes")
         

"""
src
16 00 03 01

enums
{'Axis': {'X': 0, 'Y': 1},
 'EventLogic': {'L_AND': 1, 'L_AND_NOT': 3, 'L_OR': 0, 'L_OR_NOT': 2}}

example config dict
{'base_name': 'XPP:TIMETOOL',
 'beam_logic': [{'event_code': 162L, 'logic_op': 2}],
 'calib_poly': [0.924, -0.00228, 0.0],
 'laser_logic': [{'event_code': 91L, 'logic_op': 2}],
 'project_axis': 0,
 'ref_convergence': 1.0,
 'ref_roi_hi': {'column': 1000L, 'row': 150L},
 'ref_roi_lo': {'column': 0L, 'row': 50L},
 'reference_projection_size': 0L,
 'sb_convergence': 0.05,
 'sb_roi_hi': {'column': 1000L, 'row': 150L},
 'sb_roi_lo': {'column': 0L, 'row': 0L},
 'sideband_projection_size': 0L,
 'sig_roi_hi': {'column': 1000L, 'row': 450L},
 'sig_roi_lo': {'column': 0L, 'row': 300L},
 'signal_cut': 0L,
 'signal_projection_size': 0L,
 'subtract_sideband': 1L,
 'use_reference_roi': 0L,
 'weights': [0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.02,
  0.01999,
  0.01999,
  0.01999,
  0.01998,
  0.01997,
  0.01996,
  0.01995,
  0.01993,
  0.01991,
  0.01987,
  0.01983,
  0.01978,
  0.01972,
  0.01963,
  0.01953,
  0.0194,
  0.01924,
  0.01905,
  0.01881,
  0.01854,
  0.01821,
  0.01782,
  0.01737,
  0.01685,
  0.01626,
  0.01559,
  0.01484,
  0.01401,
  0.01308,
  0.01208,
  0.01099,
  0.00981,
  0.00857,
  0.00725,
  0.00588,
  0.00445,
  0.00299,
  0.0015,
  0.0,
  -0.0015,
  -0.00299,
  -0.00445,
  -0.00588,
  -0.00725,
  -0.00857,
  -0.00981,
  -0.01099,
  -0.01208,
  -0.01308,
  -0.01401,
  -0.01484,
  -0.01559,
  -0.01626,
  -0.01685,
  -0.01737,
  -0.01782,
  -0.01821,
  -0.01854,
  -0.01881,
  -0.01905,
  -0.01924,
  -0.0194,
  -0.01953,
  -0.01963,
  -0.01972,
  -0.01978,
  -0.01983,
  -0.01987,
  -0.01991,
  -0.01993,
  -0.01995,
  -0.01996,
  -0.01997,
  -0.01998,
  -0.01999,
  -0.01999,
  -0.01999,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02,
  -0.02],
 'write_image': 1L,
 'write_projections': 0L}
"""
