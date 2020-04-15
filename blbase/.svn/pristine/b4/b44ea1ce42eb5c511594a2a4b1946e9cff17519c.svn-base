"""
Module to hold all motor objects in one place and to have group methods that
act on multiple motors.
"""
import os
import re
import threading
from types import MethodType
from psp import PV
from blbase.motor import Motor
import blbase.motorPresets as motorPresets
from blutil.threadtools import PycaThreadPool
from blutil.doctools import argspec
from blutil.organize import SimpleContainer


def interpret_motors(*motors):
    """
        motors can be lists, tuples, dictionaries, or Motor objects.

        list/tuples become the arguments used to make the Motor object.
            for example, if we do:
            Motors.add_motors(["XPP:USR:MMS:01", "m1"], ["PVNAME", "name"])
            then Motor("XPP:USR:MMS:01", "m1")
            and  Motor("PVNAME", "name")
            will be created.

        dictionaries work much the same way, but use keyword arguments:
            Motors.add_motors(dict(name="m1", pvname="XPP:USR:MMS:01"))
            is the same as adding
            Motor(name="m1", pvname="XPP:USR:MMS:01")

        list/tuples that have exactly two items, where the first is a list and
        the second is a dictionary, will be treated as a hybrid between the
        two inputs:
            Motors.add_motors([("XPP:USR:MMS:01", "m1"), dict(home=None)])
            is the same as adding
            Motor("XPP:USR:MMS:01", "m1", home=None)
    """
    mots = []
    for args in motors:
        if isinstance(args, (list, tuple)):
            if (len(args) == 2
                and isinstance(args[0], (list, tuple))
                and isinstance(args[1], dict)):
                mot = Motor(*args[0], **args[1])
            else:
                mot = Motor(*args)
        elif isinstance(args, dict):
            mot = Motor(**args)
        else:
            try:
                args.name
                mot = args
            except:
                print "Invalid arguments {}!".format(args)
                continue
        if mot.name is None:
            print "Motor {} has no valid name!".format(pv)
            continue
        mots.append(mot)
    return mots


class Motors(object):
    """
    Holds Motor objects and contains utilities for setting up motors.

    Every Motor object added can be found inside the Motors.all.m container.
    Motors can optionally be added into other groups so that they can be found
    together under Motors.groups.group_name.m.

    Each group (including Motors.all) will have group methods to act on all
    Motors in the group.
    """
    def __init__(self):
        self.all = Group(self, "all")
        self.groups = Groups(self)

    def add(self, *motors, **opts):
        """
        Include motors in this object, optionally in a group by **opts as:
            group=<string>: add motors to the group designated by <string>,
                            or add group with motors if necessary
            allow_duplicates=<bool> : if False, do not add a motor that
                                      already exists in the target group.
        """
        mots = interpret_motors(*motors)
        group = opts.pop("group", None)
        self.all._add(*mots, **opts)
        if group is not None and group != "all":
            self.groups._add(group, *mots, **opts)
    add.__doc__ += interpret_motors.__doc__

    def import_cfg(self, file_path):
        """
        Import a space-delimited file of arguments to the Motor constructor.
        """
        objs = generic_cfg.read_config(file_path)
        self.add(*objs)

    def import_epicsArch(self, file_path, regex=".*:(MMS|MMN|MZM|DMX|IMS):.*",
                         skip_import=[]):
        """
        Imports all motor pvs and names from a given epicsArch file. By
        default, only grabs pvs that contain :MMS: or :MMN:, but you can
        change the selection criteria by picking a different regex.

        These motors will be grouped under the filename, without the .txt

        If a list of Motor objects is provided to skip_import, we'll use these
        Motor objects when applicable instead of creating a new Motor object.
        """
        arch_list = self._epicsArch_load(file_path)
        mots = []
        pattern = re.compile(regex)

        skip_dict = {m.pvname : m for m in skip_import if hasattr(m, "pvname")}

        done_flags = []
        conn_pvs = []

        for d in arch_list:
            pv = d["pv"]
            alias = d["alias"]
            if pattern.match(pv):
                pv = pv.split(".")[0]
                if pv in skip_dict:
                    mots.append(skip_dict[pv])
                    continue

                # Check that RTYP field exists and is a valid motor type
                # Implement with EPICS callback
                done_flag = threading.Event()
                done_flags.append(done_flag)
                rtyp = pv + ".RTYP"
                check_pv = PV(rtyp, monitor=True)
                check_pv.add_monitor_callback(
                    append_motor_cb(check_pv, pv, alias, mots, done_flag))
                check_pv.do_initialize = True
                check_pv.connect()
                conn_pvs.append(check_pv)

        all_done = threading.Thread(target=wait_all, args=(done_flags,))
        all_done.start()
        all_done.join(1.0)

        # Disconnect the pvs, we don't need them.
        for pv_obj in conn_pvs:
            pv_obj.disconnect()

        group_name = file_path.split("/")[-1].split(".")[0]
        self.add(*mots, group=group_name, allow_duplicates=False)
        return self.groups.get(group_name)

    def _epicsArch_load(self, file_path, load_set=None):
        """
        Reads epicsArch file. Returns list of dict with keys "alias" and "pv".

        file_path is the full path to the epicsArch file to import.
        load_set is the set of full paths that we've already loaded. This lets
            us avoid infinite recursion. With epicsArch files pointing to each
            other. Always use the default argument here.
        """
        if load_set is None:
            load_set = set()
        if file_path in load_set:
            return []
        else:
            load_set.add(file_path)

        arch_list = []
        try:
            dirname = os.path.dirname(os.path.abspath(file_path))
            with(open(file_path, "r")) as f:
                sub_files = []
                alias = None
                for full_line in f:
                    # Remove comments, EOL characters, and whitespace
                    line = re.split("#|\n|\r", full_line)[0].strip()
                    if len(line) != 0:
                        if line[0] == "<":
                            sub_files.append(dirname + "/" + line[1:].strip())
                            alias = None
                        elif line[0] == "*":
                            alias = line[1:].strip()
                        else:
                            if alias is None:
                                alias = re.sub(":", "_", line.split('.')[0])
                            arch_list.append(dict(pv=line, alias=alias))
                            alias = None
        except Exception, exc:
            print "{0}: {1}".format(exc.__class__.__name__, exc)
            return arch_list

        for sub_file in sub_files:
            sub_arch = self._epicsArch_load(sub_file, load_set)
            arch_list.extend(sub_arch)

        return arch_list

    def load_preset_defaults(self):
        """
        Uses motorPresets module to apply the default presets to the
        corresponding motors.
        """
        motorPresets.load_preset_defaults(self.all.get_motors())

def append_motor_cb(rtyp_obj, pv, alias, mots, done_flag):
    motor_rtyp = ("ims", "xps8p", "arcus", "dmx")

    def motor_cb(e=None):
        if e is None and not done_flag.is_set():
            if rtyp_obj.value in motor_rtyp:
                mots.append((pv, alias))
            done_flag.set()

    return motor_cb

def wait_all(flags):
    for f in flags:
        f.wait(1.0)


class Groups(object):
    """
    Contains all the Group objects.
    """
    def __init__(self, motors_obj):
        self._groups = {}
        self._motors_obj = motors_obj

    def add(self, group_name, *motors, **opts):
        """
        Add group_name with motors to group, or extend group_name with motors.
        """
        self._motors_obj.add(*motors, group=group_name, **opts)
    add.__doc__ += interpret_motors.__doc__

    def _add(self, group_name, *motors, **opts):
        """
        The direct call to add motors to group_name.
        """
        try:
            group = self._groups[group_name]
        except:
            group = Group(self._motors_obj, group_name)
            self._groups[group_name] = group
            setattr(self, group_name, group)
        group._add(*motors, **opts)

    def get(self, group_name):
        """
        return the group associated with group_name
        """
        return self._groups[group_name]


class Group(object):
    """
    Group motors together to apply group methods.
    """
    def __init__(self, motors_obj, name):
        self._motors_obj = motors_obj
        self._name = name
        self._motors = set()
        self._pvnames = set()
        self.m = SimpleContainer()
        self.add_group_methods(
            "auto_setup",
            "clear_pu",
            "clear_stall",
            "clear_error",
            "wait",
            "stop",
            )

    def add(self, *motors, **opts):
        """
        Add motors to this group.
        """
        self._motors_obj.add(*motors, group=self._name, **opts)
    add.__doc__ += interpret_motors.__doc__

    def _add(self, *motors, **opts):
        """
        The direct call to add motors to this group.
        """
        allow_duplicates = opts.get("allow_duplicates", True)
        for motor in motors:
            if allow_duplicates or motor.pvname not in self._pvnames:
                self._motors.add(motor)
                self._pvnames.add(motor.pvname)
                setattr(self.m, motor.name, motor)

    def get_motors(self):
        """
        Return a list of all motors in the group, sorted alphabetically by
        motor name.
        """
        mots = list(self._motors)
        mots.sort(key=lambda m: m.name)
        return mots

    def get_preset_group(self):
        """
        Return a motor preset group object for the collection of motors in
        this group.
        """
        return motorPresets.PresetGroup(self.get_motors(), name=self._name)

    def map(self, func):
        """
        Call func(motor) for every motor in this group.
        Return values in the same order as get_motors().
        """
        pool = PycaThreadPool()
        return pool.map(func, self.get_motors())

    def map_method(self, method, *args, **kwargs):
        """
        Call motor.method(*args, **kwargs) for every motor in this group.
        Return values in the same order as get_motors. Skip motors that are
        missing the method.
        """
        def func(motor):
            try:
                return getattr(motor, method)(*args, **kwargs)
            except AttributeError:
                pass
            except Exception, exc:
                print "Exception for {0}: {1}".format(motor.name, exc)
        return self.map(func)

    def add_group_methods(self, *methods):
        """
        Add group method to Group object, so that group.method() is the same
        as calling motor.method() for all motors. Methods will return values
        in the same order as get_motors. Method arguments should be strings.
        """
        for func in methods:
            method = self._group_method_factory(func)
            setattr(self, func, MethodType(method, self))

    def _group_method_factory(self, func):
        """
        Create a group method and give it a reasonable docstring.
        """
        def method(self, *args, **kwargs):
            return self.map_method(func, *args, **kwargs)
        method.__name__ = func
        class_func = getattr(Motor, func)
        method.__doc__ = argspec(class_func)
        try:
            method.__doc__ += "\n" + class_func.__doc__
        except Exception:
            pass
        return method

