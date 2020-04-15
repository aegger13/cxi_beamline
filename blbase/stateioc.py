import psp.Pv as pv
from types import MethodType

def myFormat(state):
    return "_" + state.lower()
"""
myFormat Examples:
return "_" + state.lower()                  -> move_out(), is_out()
return state                                -> moveOUT(), isOUT()
return state[0].upper() + state[1:].lower() -> moveOut(), isOut()
"""

class stateiocDevice:
    """
    Class that is a catch-all for any device that has an updated motion IOC to
    move it to a number of well-defined discrete states.

    Common Features of these IOCs:
    -mbbo records at the base that return the current state,
    -mbbi records at :GO that allow us to move to a state,
    -booleans at :STATE that tell us if we're at the state.
    -floats at :STATE_SET that save the state's value
    """
    _strFields = ["ZRST", "ONST", "TWST", "THST", "FRST", "FVST", "SXST",
                  "SVST", "EIST", "NIST", "TEST", "ELST", "TVST", "TTST",
                  "FTST", "FFST"]
    _badStates = ["unknown"]

    def __init__(self, PV):
        """
        Builds all of the object's methods from the PV. You can expect the
        object to have methods like move_in, move_out, etc. for each position
        of the device.
        """
        self._PV = pv.Pv(PV)
        self._PVGO = pv.Pv(PV + ":GO")
        self._mbbiStates = []
        self._mbboStates = []
        mbbiPVs = [None] * 16
        mbboPVs = [None] * 16
        for i in range(16):
            fld = self._strFields[i]
            mbbiPVs[i] = pv.Pv("{0}.{1}".format(PV, fld), initialize=True)
            mbboPVs[i] = pv.Pv("{0}:GO.{1}".format(PV, fld), initialize=True)
        for i in range(16):
            mbboPVs[i].wait_ready()
            outStr = mbboPVs[i].get()
            if outStr == "":
                break
            mbbiPVs[i].wait_ready()
            inStr = mbbiPVs[i].get()
            self._mbbiStates += [inStr]
            self._mbboStates += [outStr]
        nStates = len(self._mbbiStates)
        self._statePVs = [None] * nStates
        self._setPVs = [None] * nStates
        self._deltaPVs = [None] * nStates
        for i in range(nStates):
            state = self._mbboStates[i]
            if state.lower() not in self._badStates:
                self._statePVs[i] = pv.Pv("{0}:{1}".format(PV, state))
                self._setPVs[i] = pv.Pv("{0}:{1}_SET".format(PV, state))
                self._deltaPVs[i] = pv.Pv("{0}:{1}_DELTA".format(PV, state))
                self._addMethods(i, self._mbbiStates[i])
        # Temporary wait handler while the IOC doesn't directly support wait
        self._lastMove = self._PV.get()

    def move(self, state):
        """ Moves motor to state. Useful for scripting (no tab completion) """
        index = self._stateToIndex(state)
        if index >= 0:
            self._move(index)

    def _move(self, index):
        self._lastMove = index
        self._PVGO.put(index)

    def isat(self, state):
        """ Checks if motor is in state. Useful for scripting. """
        index = self._stateToIndex(state)
        if index >= 0:
            return self._is(index)

    def _is(self, index):
        return bool(self._statePVs[index].get())

    def _stateToIndex(self, state):
        try:
            return self._mbboStates.index(state)
        except StandardError:
            try:
                return self._mbbiStates.index(state)
            except StandardError:
                print "State {0} not found.".format(state)
                return -1

    def state(self):
        """ Returns the state of this motor. """
        return self._mbbiStates[self._PV.get()]

    def statesAll(self):
        states = []
        for s in self._mbbiStates:
            if s.lower() not in self._badStates:
                states.append(s)
        return states

    def posAll(self):
        pos = []
        for s in self._mbbiStates:
            if s.lower() not in self._badStates:
                thisPos = self.statePos(s)
                pos.append(thisPos)
        return pos

    def statePos(self, state):
        """ Gets the set position of state. """
        index = self._stateToIndex(state)
        if index >= 0:
            return self._getPos(index)

    def _getPos(self, index):
        return self._setPVs[index].get()

    def statePosAll(self):
        """ Returns all set positions as a dictionary. """
        d = {}
        for inS, outS in zip(self._mbboStates, self._mbbiStates):
            if inS.lower() not in self._badStates:
                d[outS] = self.statePos(inS)
        return d

    def setStatePos(self, state, pos):
        """ Sets the state's position in the IOC. """
        index = self._stateToIndex(state)
        if index >= 0:
            self._setPos(index, pos)

    def _setPos(self, index, pos):
        self._setPVs[index].put(pos)

    def stateDelta(self, state):
        """ Gets the delta (allowed deviation) of state. """
        index = self._stateToIndex(state)
        if index >= 0:
            return self._getDelta(index)

    def _getDelta(self, index):
        return self._deltaPVs[index].get()

    def setStateDelta(self, state, delta):
        """ Sets the state's delta (allowed deviation) in the IOC. """
        index = self._stateToIndex(state)
        if index >= 0:
            self._setDelta(index, delta)

    def _setDelta(self, index, delta):
        self._deltaPVs[index].put(delta)

    def wait(self):
        """
        Checks if the motor is in the last position it was told to move to.
        If not, waits until the motor is in this position.
        """
        self._PV.wait_for_value(self._lastMove)

    def _addMethods(self, index, inS):
        def moveMethod(self):
            """ Moves this motor to the designated state. """
            return self._move(index)
        def isMethod(self):
            """ Returns true if motor is in the designated state. """
            return self._is(index)
        def getPosMethod(self):
            """ Gets the value for position in the IOC """
            return self._getPos(index)
        def setPosMethod(self, pos):
            """ Sets the value for position in the IOC """
            self._setPos(index, pos)
        def getDeltaMethod(self):
            """ Gets the value for delta in the IOC """
            return self._getDelta(index)
        def setDeltaMethod(self, delta):
            """ Sets the value for delta in the IOC """
            self._setDelta(index, delta)
        bindMethod(self, "move" + myFormat(inS), moveMethod)
        bindMethod(self, "is"   + myFormat(inS), isMethod)
        bindMethod(self, "getPos" + myFormat(inS), getPosMethod)
        bindMethod(self, "setPos" + myFormat(inS), setPosMethod)
        bindMethod(self, "getDelta" + myFormat(inS), getDeltaMethod)
        bindMethod(self, "setDelta" + myFormat(inS), setDeltaMethod)

def bindMethod(obj, methodName, method):
    setattr(obj, methodName, MethodType(method, obj))

