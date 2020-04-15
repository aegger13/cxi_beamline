from types import MethodType          # MethodType to properly bind methods
import simplejson as json             # json to save/load presets
import os.path                        # os.path to check directories
import os                             # os to make folders
import motor as mot ###               # Motor to create objs on group load

# Lines marked by ### depend on implementation of Motor class
# Two ## depends on some other file

# Choose a default folder for all preset saves
_presetFolder = None
def set_presetFolder(folder):
    global _presetFolder
    _presetFolder = folder

def ready():
    return _presetFolder is not None

def _checkFolder():
    if _presetFolder is None:
        raise Exception("Cannot create presets. Please specify a preset" +
            "folder using motorPresets.set_presetFolder during setup.")

# Text format for methods. {0} is replaced with the preset name.
_moveFormat  = "mv_{0}"
_umvFormat   = "umv_{0}"
_wmFormat    = "wm_{0}"
_isFormat    = "is_{0}"
_stateFormat = "state"

"""
Useful Functions in Global Namespace:

loadPresets(): tries to find the alwaysLoad.cfg file and loads it. Returns a
               dictionary {motorName : presetFile} and stores it in the
               namespace of this module under motorPresets.loaded. Does not
               reload on subsequent calls unless you call it with reload=True

presetFile(motorName): Uses the loaded dictionary to return the preset file
                       associated with the input motor name in alwaysLoad.cfg.
                       This is the file to pass into the MotorPresets object
                       to load the associated presets.
"""
loaded = {}
def loadPresets(reload=False):
    """
    On first call, return all presets in the alwaysLoad.cfg file.
    On subsequent calls, return the previously loaded presets.
    """
    _checkFolder()
    global loaded
    if reload or not loaded:
        presetIndex = _presetFolder + "alwaysLoad.cfg"
        try:
            f = open(presetIndex)
            loaded = json.load(f)
            f.close()
        except StandardError as e:
            print "Motor preset index file alwaysLoad.cfg failed to load."
            print e
    return loaded

def presetFile(motorName):
    """
    Return the presets from a single motor.
    """
    return loadPresets()[motorName]

def load_preset_defaults(motor_list):
    """
    Load the default presets into a list of motor objects.
    """
    ok = 0
    bad = 0
    print "Loading default presets..."
    for mot in motor_list:
        try:
            file = presetFile(mot.name)
            MotorPresets(mot, loadFile=file, auto_sync=True)
            ok += 1
        except Exception:
            bad += 1
    print "Done loading presets."
    print "{0} loaded successfully, {1} skipped.".format(ok, bad)

class MotorPresets(object):
    """
    Class that represents a set of presets associated with one motor.

    Initialization:
    >>> preset = MotorPresets(motor, loadFile=None, comment="")
    -motor is the motor this preset operates on
    -loadFile is the optional file string to load on init
    -comment is optional comment field. If a comment exists in loadFile,
     the loaded comment will take precedence.

    Methods:
    .add(name, pos)  adds preset name as position pos
    .addHere(name)   adds preset name at current position
    .remove(name)    removes specified preset
    .removeAll()     removes all presets
    .save(filename)  saves the preset dictionary to filename
    .load(filename)  loads preset dictionary from filename and applies it
    .sync()          loads preset dictionary if it has been updated
    .mv_preset(name) convenience method for calling move_preset() in script
    .umv_preset(name) same as mv_preset but with position updating
    .is_at(name)     returns True if within delta of state noted be name
    .state()         returns the preset position this motor is in, or unknown
    .wm(name)        returns motor position relative to name
    .info()          prints information about this preset
    .posVal(name)  return positional value of name
    .showPreset(name) print information about name
    .allPresets()    returns the json preset positions dictionary
    .add(dict)       alternative syntax to add a {name : pos} dict to object
    .make_group()    returns a PresetGroup with just this object in it.

    When a preset is added to this object, the motor gets new methods as
    described by the format strings below this docstring. These are currently:
    .mv_preset()   moves motor to the preset position
    .umv_preset()    moves motor to the preset position, updating the user
    .wm_preset()     returns motor position relative to preset
    .is_preset()     returns True if motor is within .delta of preset
    .state()         returns current state of motor or unknown

    Note that once a filename is chosen, it becomes the default and files can
    be managed as .save() and .load(). The original default filename is
    motorName_presets.txt. All file paths are relative to ./presets

    You can also try something like:
    >>> MotorPresets(motor, myfile.txt)
    to add preset methods to the motor object if you won't need the presets
    object after an initial load.

    You can always access the original presets object at motor.presets.
    """
    delta = 0.5 # allowable deviation from positions
    
    def __init__(self, motor, loadFile=None, comment="", auto_sync=True):
        """
        motor is a valid motor object
        loadFile is a string path to a motorPresets save file. If included,
            presets will be loaded on init.
        comment is a string comment associated with this preset. This may
            be overwritten on a load if the file has a comment.
        auto_sync will save after every add/set/remove.
        """
        _checkFolder()
        self.motor = motor
        motor.presets = self ###
        self._positions = {}
        self._defaultFilename = self.motor.name + "_presets.txt" ###
        self.comment = comment
        if not os.path.exists(_presetFolder):
            os.mkdir(_presetFolder)
        self._groups = []
        if loadFile is not None:
            self.load(loadFile)
        elif auto_sync:
            ok = self.load(doPrint=False)
            if not ok:
                self._sync_time = None
        else:
            self._sync_time = None
        self.auto_sync=auto_sync
        def statePreset(self):
            return self.presets.state()
        self._newMethod(_stateFormat, statePreset)

    def __call__(self, name, pos=None, doPrint=True, use_auto_sync=True):
        """
        add a preset to the connected motor object, creating the various
        preset methods. If pos is omitted, add the preset at this location.
        """
        return self.add(name, pos, doPrint, use_auto_sync)
 
    def add(self, name, pos=None, doPrint=True, use_auto_sync=True):
        """
        add a preset to the connected motor object, creating the various
        preset methods. If pos is omitted, add the preset at this location.
        """
        if type(name) is dict:
            for n, p in name.items():
                self.add(n, p)
        elif name == "comment":
            print "comment is an invalid preset name."
        elif pos is None:
            self.addHere(name)
        else:
            if use_auto_sync and self.auto_sync:
                self.sync()
            self._positions[name] = pos
            self._newPresetMethods(name, pos)
            for group in self._groups:
                group._addNameObjLink(name, self)
            if doPrint:
                print "Preset {0} added.".format(name)
            if use_auto_sync and self.auto_sync:
                self.save()

    def addHere(self, name):
        """
        call add for this location
        """
        self.add(name, self.motor.wm()) ###

    def set(self, name, pos=None, doPrint=True):
        """
        add a preset to the connected motor object, creating the various
        preset methods. If pos is omitted, add the preset at this location.
        """
        self.add(name, pos, doPrint)

    def remove(self, name, doPrint=True, use_auto_sync=True):
        """
        Remove a preset position and the corresponding methods.
        If self.auto_sync is true, changes saved files as well.
        """
        try:
            del self._positions[name]
            delattr(self.motor, _moveFormat.format(name))
            delattr(self.motor, _umvFormat.format(name))
            delattr(self.motor, _wmFormat.format(name))
            delattr(self.motor, _isFormat.format(name))
            for group in self._groups:
                group._rmNameObjLink(name, self)
            if doPrint:
                print "Preset {0} removed.".format(name)
            if use_auto_sync and self.auto_sync:
                self.save()
            return True
        except StandardError as e:
            print "Could not remove preset named {0}. {1}".format(name, e)
            return False

    def removeAll(self, doPrint=True):
        """
        Remove all presets positions and corresponding methods.
        Only changes the live object, not any saved files.
        """
        origPos = self._positions.copy()
        noErrors = True
        for name in origPos:
            noErrors = noErrors and self.remove(name, doPrint=doPrint, use_auto_sync=False)
        return noErrors

    def save(self, filename=None, comment=None):
        """
        Saves object's current preset positions to filename with comment.
        If filename is omitted, the most recently used filename for this
        object is used. If no such name exists, a default is used.

        Filenames can be absolute, or relative to the presets folder.
        """
        filename = self._adjustFilename(filename)
        if comment is not None:
            self.comment = comment
        print "Saving..."
        try:
            with open(filename, "w") as f:
                f.write(self._posAndCommentJson())
            didSave = True
        except StandardError as e:
            print "Save failed. {0}".format(e)
            didSave = False
        finally:
            print "Save completed."
            return didSave

    def load(self, filename=None, doPrint=False):
        """
        Loads object's preset positions from filename.
        If filename is omitted, the most recently used filename for this
        object is used. If no such name exists, a default is used.

        Filenames can be absolute, or relative to the presets folder.
        """
        filename = self._adjustFilename(filename)
        try:
            with open(filename, "r") as f:
                newPos = json.load(f)
            self.removeAll(doPrint=doPrint)
            for name, pos in newPos.items():
                if name == "comment":
                    self.comment = pos
                else:
                    self.add(name, pos, doPrint=doPrint, use_auto_sync=False)
            self._sync_time = os.path.getmtime(filename)
            didLoad = True
        except StandardError as e:
            if doPrint:
                print "Load failed. {0}".format(e)
            didLoad = False
        return didLoad

    def sync(self):
        """
        Checks to see if this object is out of date, based on update time
        of the loaded file. If out of date, load. This should be run prior to
        every save if auto_sync is True to avoid overwriting things.
        """
        if self._sync_time is None or self._sync_time < os.path.getmtime(self._adjustFilename(None)):
            return self.load(doPrint=False)
        return False

    def _posAndCommentJson(self):
        """Prepare preset dictionary for saving"""
        d = self._positions.copy()
        d["comment"] = self.comment
        return jsonFormat(d)

    def mv_preset(self, name):
        """Move to preset specifed by string name"""
        pos = self._positions[name]
        self.motor.move(pos) ###

    def umv_preset(self, name):
        """Update move to preset specified by string name"""
        pos = self._positions[name]
        self.motor.update_move(pos) ###

    def is_at(self, name):
        """Return True if motor is within self.delta of preset name""" 
        namePos = self._positions[name]
        currPos = self.motor.wm() ###
        return abs(currPos - namePos) < self.delta

    def state(self):
        """Return the name of the state this motor is at, or unknown"""
        for name in self._positions:
            if self.is_at(name):
                return name
        return "unknown"

    def wm(self, name):
        """Return the motor's offset from preset string name"""
        return self._positions[name] - self.motor.wm() ###

    def info(self, doPrint=True):
        """
        Print info of motor, presets, and current position.
        """
        d = {
               "motor"   : self.motor.name, ###
               "states"  : self._positions, ###
               "current" : self.state(),
               "pos"     : self.motor.wm() ###
            }
        if doPrint:
            print jsonFormat(d)
        else:
            return d

    def posVal(self, name):
        """Return the position value of preset name"""
        return self._positions[name]

    def showPreset(self, name, doPrint=True):
        """Print info about preset name"""
        d = {
              "motorName"  : self.motor.name, ###
              "presetName" : name,
              "presetPos"  : self.posVal(name),
              "currentPos" : self.motor.wm(), ###
              "delta"      : self.wm(name)
            }
        if doPrint:
            print jsonFormat(d)
        else:
            return d

    def allPresets(self, doPrint=True):
        """Print all presets"""
        if doPrint:
            print jsonFormat(self._positions)
        else:
            return self._positions.copy()

    def make_group(self, name=""):
        """Return a PresetGroup with just this preset in it."""
        return PresetGroup(presetObj=self, name=name)

    def _adjustFilename(self, filename):
        """Select default filename if needed and adjust for relative paths"""
        if filename is None:
            filename = self._defaultFilename
        else:
            self._defaultFilename = filename
        return fileExt(filename)

    def _newMethod(self, methodName, func):
        """Add method to the associated motor."""
        bindMethod(self.motor, methodName, func)

    def _newPresetMethods(self, name, pos):
        """Add methods associated with one preset position"""
        pObj = self
        def mvPreset(self):
            self.move(pos) ###
        def umvPreset(self):
            self.update_move(pos) ###
        def wmPreset(self):
            return pObj.wm(name)
        def isPreset(self):
            return pObj.is_at(name)
        moveStr = _moveFormat.format(name)
        umvStr  = _umvFormat.format(name)
        wmStr   = _wmFormat.format(name)
        isStr   = _isFormat.format(name)
        self._newMethod(moveStr, mvPreset)
        self._newMethod(umvStr, umvPreset)
        self._newMethod(wmStr, wmPreset)
        self._newMethod(isStr, isPreset)

    def _showPresetFolder(self): # just in case you want to check it...
        """Return the default folder for saving preset files."""
        return _presetFolder

    def __repr__(self):
        return "<MotorPresets obj {0}, {1}>".format(self.motor.name, self.comment) ###

    def __str__(self):
        return "<MotorPresets obj {0}>".format(self.motor.name)

 
class PresetGroup(object):
    """
    Class that represents a group of MotorPresets objects.

    Initialization:
    >>> group = PresetGroup(presetObj=[], loadFile=None)
    -presetObj is MotorPresets object or a list of such objects to include
    -loadFile is the optional group file string to load at init

    Methods:
    .add(presetObj)    adds additional presets after the initial init
    .remove(presetObj) removes a preset from the group
    .removeAll()       removes all presets from the group
    .save(filename)    saves all presets and the presetgroup
    .load(filename)    loads the preset group, does not add methods to motors
    .state()           prints the current preset positions of all motors
    .info()            prints verbose information about all presets in group
    .group_move(name)  moves all motors in the group to name if applicable
    .group_umv(name)   does move, but updates on all applicable motors too
    .group_wm(name)    returns pos relative to name for applicable motors
    .group_is(name)    returns is_name booleans for applicable motors

    This object does NOT touch the methods of individual motor objects. Due to
    the way that python namespaces work, this module can never have access to
    a list of motors in the current interactive session, unless we pass them
    into these objects in an unintuitive way. This class adds methods to
    itself that call the motor object preset methods. This is so the preset
    positions can be found with tab completeion.

    The additional methods are:
    .mv_preset()     moves all motors in the group to preset if applicable
    .umv_preset()      does move, but updates on all applicable motors too
    .wm_preset()       returns pos relative to preset for applicable motors
    .is_preset()       returns is_preset booleans for applicable motors
     
    Motors with identically named preset positions will be moved together.
    Similarly, when we call wm_preset or is_preset we get information about
    any motors with this named preset position.
    """
    def __init__(self, presetObj=[], loadFile=None, name=""):
        _checkFolder()
        self._groupMap = {}
        self._presetSet = set()
        if loadFile is not None:
            self.load(loadFile)
        self.add(presetObj)
        self.name = name

    def add(self, presetObj, doPrint=True):
        if type(presetObj) in [list, set]:
            for obj in presetObj:
                self.add(obj)
            return
        if isinstance(presetObj, mot.Motor):
            try:
                presetObj = presetObj.presets
            except:
                presetObj = MotorPresets(presetObj)
        if presetObj in self._presetSet:
            print "Cannot add preset already in group."
        else:
            for name in presetObj._positions:
                self._addNameObjLink(name, presetObj)
            self._presetSet.add(presetObj)
            presetObj._groups += [self]
            if doPrint:
                print "Added preset {0} to group.".format(presetObj)

    def remove(self, presetObj, doPrint=True):
        try:
            for name in presetObj._positions:
                self._rmNameObjLink(name, presetObj)
            self._presetSet.remove(presetObj)
            presetObj._groups.remove(self)
            if doPrint:
                print "Removed preset {0} from group.".format(presetObj)
            return True
        except StandardError as e:
            print "Error in removing {0} from group. {1}".format(presetObj, e)
            return False

    def removeAll(self, doPrint=True):
        oldSet = self._presetSet.copy()
        noErrors = True
        for presetObj in oldSet:
            noErrors = noErrors and self.remove(presetObj, doPrint=doPrint)
        return noErrors

    def _addNameObjLink(self, name, presetObj):
        if name not in self._groupMap:
            self._groupMap[name] = [presetObj]
            self._newGroupMethods(name)
        else:
            self._groupMap[name] += [presetObj]

    def _rmNameObjLink(self, name, presetObj):
        if self._groupMap[name] == [presetObj]:
            del self._groupMap[name]
            delattr(self, _moveFormat.format(name))
            delattr(self, _umvFormat.format(name))
            delattr(self, _wmFormat.format(name))
            delattr(self, _isFormat.format(name))
        else:
            self._groupMap[name].remove(presetObj)

    def save(self, filename, saveType="pv"):
        pvfiles = {}
        for preset in self._presetSet:
            if saveType == "pv":
                id = preset.motor.pvname ###
            elif saveType == "name":
                id = preset.motor.name ###
            else:
                print "Invalid saveType {0}".format(saveType)
                return False
            preset.save()
            file = preset._defaultFilename
            pvfiles[id] = os.path.abspath(fileExt(file))
        pvfiles["_name"] = self.name
        pvfiles["_saveType"] = saveType
        text = jsonFormat(pvfiles)
        filename = fileExt(filename)
        try:
            with open(filename, "w") as f:
                f.write(text)
            didSave = True
        except StandardError as e:
            print "Save failed. {0}".format(e)
            didSave = False
        return didSave

    def load(self, filename, doPrint=True):
        filename = fileExt(filename)
        try:
            with open(filename, "r") as f:
                d = json.load(f)
            saveType = d["_saveType"]
            if saveType == "pv":
                _pvLoad(d)
                didLoad = True
            elif saveType == "name":
                _nameLoad(d)
                didLoad = True
            else:
                print "Load file corrupted. Invalid saveType found."
                didLoad = False
        except StandardError as e:
            print "Load failed {0}".format(e)
            didLoad = False
        if didLoad and doPrint:
            print "Load successful."
        return didLoad

    def _pvLoad(d):
        for pv, file in d.items():
            if pv == "_name":
                self.name = file
            else:
                preset = MotorPresets(mot.Motor(pv), loadFile=file)
                self.add(preset)
        didLoad = True

    def _nameLoad(d):
        didNothing = True
        for preset in self._presetSet:
            if preset.motor.name in d: ###
                preset.load(d[name])
                didNothing = False
        if didNothing:
            print "WARNING: No motors in this group were found in load file."
            print "Add motors to group before loading this file."

    def state(self, doPrint=True):
        d = {}
        for preset in self._presetSet:
            d[preset.motor.name] = preset.state() ###
        if len(d) == 0:
            return "No presets in group."
        elif doPrint:
            print jsonFormat(d)
        else:
            return d

    def info(self, doPrint=True):
        d = {}
        for preset in self._presetSet:
            d[preset.motor.name] = preset.info(doPrint=False)
        if doPrint:
            print jsonFormat(d)
        else:
            return d

    def showPreset(self, name, doPrint=True):
        d = {}
        for preset in self._presetSet:
            if name in preset._positions:
                d[preset.motor.name] = preset.showPreset(doPrint=False) ###
        if doPrint:
            print "Showing preset {0}:".format(name)
            print "{0:^10}{1:^12}{2:^12}{3:^12}".format("Motor", "PresetPos",
                                                        "MotorPos", "Delta")
            lines = []
            for value in d.values():
                lines.append("{0:^10}{1:^12.3f}{2:^12.3f}{3:^12.3f}".format(
                                              d["motorName"], d["presetPos"],
                                              d["currentPos"], d["delta"]))
                lines.sort()
            for line in lines:
                print line
        else:
            return d

    def listPresets(self, doPrint = True):
        allPresets = self._groupMap.keys()
        allPresets.sort()
        if doPrint:
            print jsonFormat(allPresets)
        else:
            return allPresets

    def group_move(self, name):
        for preset in self._groupMap[name]:
            preset.mv_preset(name)

    def group_umv(self, name):
        for preset in self._groupMap[name]:
            print "Moving {0}...".format(preset.motor.name)
            preset.umv_preset(name)
            print "Done moving {0}".format(preset.motor.name)

    def group_wm(self, name, doPrint=True):
        wmd = {}
        for preset in self._groupMap[name]:
            wmd[preset.motor.name] = preset.wm(name) ###
        if doPrint:
            print jsonFormat(wmd)
        else:
            return wmd

    def group_is(self, name, doPrint=True):
        isd = {}
        for preset in self._groupMap[name]:
            isd[preset.motor.name] = preset.is_at(name) ###
        if doPrint:
            print jsonFormat(isd)
        else:
            return isd

    def _newGroupMethods(self, name):
        moveStr = _moveFormat.format(name)
        umvStr = _umvFormat.format(name)
        wmStr = _wmFormat.format(name)
        isStr = _isFormat.format(name)
        def groupMove(self):
            self.group_move(name)
        def groupUmv(self):
            self.group_umv(name)
        def groupWm(self, doPrint=True):
            self.group_wm(name, doPrint)
        def groupIs(self, doPrint=True):
            self.group_is(name, doPrint)
        bindMethod(self, moveStr, groupMove)
        bindMethod(self, umvStr, groupUmv)
        bindMethod(self, wmStr, groupWm)
        bindMethod(self, isStr, groupIs)

    def __repr__(self):
        if self.name == "":
            return "<Unnamed preset group>"
        else:
            return "<PresetGroup {0}>".format(self.name)


def bindMethod(obj, methodName, method):
    """ Binds method to obj as methodName """
    setattr(obj, methodName, MethodType(method, obj))

def fileExt(filename):
    """
    Modifies input filename to ensure it has a file extension. If absolute
    folder is not defined, apples relative folder.
    """
    if filename[0] != "/":
        filename = "{0}{1}".format(_presetFolder, filename)
    if "." not in filename:
        filename += ".txt"
    return filename 

def jsonFormat(inputDict):
    """Enforce a consistent json format"""
    return json.dumps(inputDict, sort_keys=True, indent="  ") + "\n"

