import time
from threading import Thread
import psp.Pv as Pv
from blutil import estr, printnow
from blutil.pypslog import logprint
from blutil.edm import edm_hutch_open
from blbase.motor import Motor


MON_OPT = 'monitor'
ENUM_OPT = 'enum'
ESWITCH = 12.8
ATT_PARAMS = {  
  'EU1st':      ('EDES',        'User Input Energy (fundamental) ',     {}),
  'E1st':       ('T_CALC.VALE', 'Energy (fundamental) ',                {MON_OPT: True}),
  'Td1st':      ('R_DES',       'Desired Transmission (fundamental) ',  {}),
  'T1st':       ('R_CUR',       'Transmission (fundamental) ',          {MON_OPT: True}),
  'T1st_c':     ('R_CEIL',      'Transmission ceiling (fundamental) ',  {}),
  'T1st_f':     ('R_FLOOR',     'Transmission floor (fundamental) ',    {}),

  'EU3rd':      ('E3DES',       'User Input Energy (3rd harmonic) ',    {}),
  'E3rd':       ('T_CALC.VALH', 'Energy (3rd harmonic) ',               {MON_OPT: True}),
  'Td3rd':      ('R3_DES',      'Desired Transmission (3rd harmonic) ', {}),
  'T3rd':       ('R3_CUR',      'Transmission (3rd harmonic) ',         {MON_OPT: True}),
  'T3rd_c':     ('R3_CEIL',     'Transmission ceiling (3rd harmonic) ', {}),
  'T3rd_f':     ('R3_FLOOR',    'Transmission floor (3rd harmonic) ',   {}),

  'AttNum':     ('NATT',        'Number of filters ',                   {}),

  #set/action parameters
  'Eget':       ('EACT.SCAN',   'Eget ',                                {ENUM_OPT: True}),
  'Eapply':     ('EACT.PROC',   'Process Energy ',                      {}),
  'Mode':       ('MODE',        'Movement Mode ',                       {ENUM_OPT: True}),
  'Go':         ('GO',          'Apply/Move ',                          {ENUM_OPT: True}),
  'Status':     ('STATUS',      'Condition Readback ',                  {MON_OPT: True, ENUM_OPT: True}),
  'CalcPend':   ('CALCP',       'Requested calculation is pending',     {ENUM_OPT: True}),
}


class Filter(object):
  """ Class to define filter properties """
  NOT_STUCK = 'Not Stuck'
  STUCK_IN  = 'Stuck In'
  STUCK_OUT = 'Stuck Out'
  IN        = 'IN'
  OUT       = 'OUT'
  UNKNOWN   = 'Unknown'

  def __init__(self, PVbase, attnum):
    self.PVbase = '%s:%02d'%(PVbase, attnum)
    self._attnum = attnum
    self.__d_pv = Pv.Pv('%s:THICK'%self.PVbase)
    self.__mat_pv = Pv.Pv('%s:MATERIAL'%self.PVbase)
    self.__mat_pv.set_string_enum(True)
    self.__preset_inp = Pv.Pv('%s:STATE.INP'%self.PVbase, initialize=True)
    thread = Thread(target=self.__init_states, args=())
    thread.start()
    self.__go_pv = Pv.Pv('%s:GO'%self.PVbase)
    self.__go_pv.set_string_enum(True)
    self.__state_pv = Pv.Pv('%s:STATE'%self.PVbase, monitor=True)
    self.__state_pv.set_string_enum(True)
    self.__stuck_pv = Pv.Pv('%s:IS_STUCK'%self.PVbase, monitor=True)
    self.__stuck_pv.set_string_enum(True)
    self.__move_pv = Pv.Pv('%s:_MOVE'%self.PVbase, monitor=True)

  def d(self, thick=None):
    """ gets or sets the thickness of the filter """
    if thick is None:
      return self.__d_pv.get()
    else:
      self.__d_pv.put(thick)

  def material(self, material=None):
    """ gets or sets the material of the filter """
    if material is None:
      return self.__mat_pv.get()
    else:
      self.__mat_pv.put(thick)

  def __init_states(self):
    """ background thread to set up inpos, etc. once possible """
    self.__preset_inp.wait_ready()
    self.__preset, _, _ = self.__preset_inp.value.partition(" ")
    self.__inpos = Pv.Pv('%s:IN_SET'%self.__preset)
    self.__outpos = Pv.Pv('%s:OUT_SET'%self.__preset)
    self.__indelta = Pv.Pv('%s:IN_DELTA'%self.__preset)
    self.__outdelta = Pv.Pv('%s:OUT_DELTA'%self.__preset)

  def inpos(self, position=None):
    """ gets or sets the value of the filter preset 'in' position """
    if position is None:
      return self.__inpos.get()
    else:
      self.__inpos.put(position)

  def outpos(self, position=None):
    """ gets or sets the value of the filter preset 'out' position """
    if position is None:
      return self.__outpos.get()
    else:
      self.__outpos.put(position)

  def indelta(self, delta=None):
    """ gets or sets the value of the filter preset delta used for
        calculating the 'in' position """
    if delta is None:
      return self.__indelta.get()
    else:
      self.__indelta.put(delta)

  def outdelta(self, delta=None):
    """ gets or sets the value of the filter preset delta used for
        calculating the 'out' position """
    if delta is None:
      return self.__outdelta.get()
    else:
      self.__outdelta.put(delta)

  def movein(self):
    """ moves the attenuator filter to its preset IN position"""
    self.__go_pv.put(Filter.IN)

  def moveout(self):
    """ moves the attenuator filter to its preset OUT position"""
    self.__go_pv.put(Filter.OUT)

  def isin(self,pos=None):
    """ return True if the filter is within allowed delta from 
        the predined `in` position"""
    return self.state() == Filter.IN

  def isout(self,pos=None):
    """ return True if the filter is within allowed delta from 
        the predined `out` position"""
    return self.state() == Filter.OUT

  def state(self):
    """ returns the position state filter (IN, OUT, Unknown) """
    if not self.__state_pv.ismonitored:
      self.__state_pv.monitor_start()
    return self.__state_pv.value

  def stuck(self, state=None):
    """ returns the stuck state of the filer  (Not Stuck, Stuck In, Stuck Out)
        If a state value is passed to the function it sets the stuck state
        accordingly """
    if state is None:
      if not self.__stuck_pv.ismonitored:
        self.__stuck_pv.monitor_start()
      return self.__stuck_pv.value
    else:
      self.__stuck_pv.put(state)

  @property
  def motorpv(self):
    """ pv of the motor associated with this filter
        only calculate this the first time it is requested """
    try:
        return self.__motorpv
    except:
        self.__motorPV = Pv.get(self.PVbase + ":_MOVE.INPA").split(".")[0]
        return self.__motorPV

  def wait(self):
    """ wait for motor to stop moving """
    self.__move_pv.wait_for_value(0)

  def status(self):
    s = "attenuator %s (%d um of %s) is in position: "%(self.PVbase, self.d(), self.material())
    if self.state() == Filter.IN:
      s += estr("IN",color="green",type="normal")
    elif self.state() == Filter.OUT:
      s += estr("OUT",color="green",type="normal")
    else:
      s += estr("Unknown",color="yellow",type="normal")
    return s

  def __repr__(self):
    return self.status()


class Lusiatt(object):
  """ module to control the Lusi Si attenuators.
  main user interface:
  defined somewhere att=lusisiatt.Lusiatt(m.vector_with_filter,lcls)
  - att.getT();  # returns dictionary with attenuations at fundamental, 3rd
                 # harmonic, total, etc.; also print on screen attenuator
                 #  status
  - att.getTvalue(); # returns total transmission at the working energy as float
  - att.setT(T); # change the atenuators to best mach the required 
                 # transmission value `T`; filters are changed in a "safe" way
                 # first new filters are inserted, then the one not needed are
                 # removed; in this way the transmission is never bigger
                 # than the current or requested value
  - att.setT(T,fast=1): # as above but do ot wait for filter and move all
                 # filters at the same time; good when the beam is stopped in
                 # some way (shutter and or burst mode)
  - att.wait
  - att.setE(E): # set the current working energy to E, if called att.setE()
                 # gets the value from the machine. E can be in eV or keV
  """
  def __init__(self, PVbase, eswitch=ESWITCH, n_att=None):
    """ init function; not to be used in an explicit call """
    self.PVbase = PVbase
    self._pv_dict = self.__load_pvs()
    if n_att is None:
        self.n = self.get_par('AttNum')
    else:
        self.n = n_att
    # the switchover point from fundemental to 3rd harmonic
    self.eswitch = eswitch
    self._unit = 1e3
    self.filters = [ Filter(PVbase, i) for i in range(1, self.n+1) ]

  def __load_pvs(self):
    """ connect to all needed PVs for the attenuator and start monitoring if requested """
    pv_dict = {}
    for parname, (pvname, desc, opts) in ATT_PARAMS.iteritems():
      monitor_opt = opts.get(MON_OPT, False)
      enum_opt = opts.get(ENUM_OPT, False)
      pv = Pv.Pv('%s:COM:%s'%(self.PVbase, pvname),monitor=monitor_opt)
      if enum_opt:
        pv.set_string_enum(True)
      pv_dict[parname] = pv

    return pv_dict

  def __get_pv(self, parname):
    """ reurn handle to PV that is mapped to the requested parname """
    if parname in self._pv_dict:
      return self._pv_dict[parname]
    else:
      raise KeyError('Unknown parameter name: %s'%parname)

  def get_pvname(self, parname=''):
    """ reurn name string for PV that is mapped to the requested parname """
    if parname=='':
      return self.PVbase
    else:
      return self.__get_pv(parname).name

  def get_par(self,parname):
    """ get the latest value of the PV that is mapped to the requested parname """
    pv = self.__get_pv(parname)
    if pv.do_monitor:
      if not pv.ismonitored:
        pv.monitor_start()
      return pv.value
    else:
      return pv.get()

  def put_par(self,parname,value,wait=False):
    """ put the passed value to the PV that is mapped to the requested parname """
    pv = self.__get_pv(parname)
    pv.put(value)
    if wait:
      pv.wait_for_value(value)

  def wait_par(self, parname, value=None):
    """ wait for par to change if no value passed, otherwise wait until par equals the value """
    pv = self.__get_pv(parname)
    if value is None:
      pv.wait_until_change()
    else:
      pv.wait_for_value(value)

  @property
  def __E(self):
    """ getter for fundemental energy """
    return self.get_par('E1st') / self._unit

  @property
  def __E3(self):
    """ getter for 3rd harmonic """
    return self.get_par('E3rd') / self._unit

  @__E.setter
  def __E(self, E):
    """ setter for fundemental energy """
    self.__set_E('EU1st', 'E1st', E*self._unit)

  @__E3.setter
  def __E3(self, E3):
    """ setter for 3rd harmonic """
    self.__set_E('EU3rd', 'E3rd', E3*self._unit)

  @property
  def mode(self):
    return self.get_par('Mode')

  @mode.setter
  def mode(self, val):
    self.put_par('Mode', val)

  def __set_E(self, parname, rbvname, E):
    """ sets energy to manual mode pushes energy """
    self.put_par('Eget', "Passive", wait=True)
    self.put_par(parname, E, wait=True)
    self.wait_par(rbvname, E)

  def allIN(self):
    """ Move all filters in the beam """
    self.put_par('Go', 'All IN')

  def allOUT(self):
    """ Move all filters out of the beam """
    self.put_par('Go', 'All OUT')

  def wait(self):
    """ waits for the motors to stop moving """
    pv = self.__get_pv('Status')
    pv.wait_for_value('OK')

  def clear(self):
    """ Clear the faulted move state """
    self.put_par('Status', 'OK', wait=True)

  def getT3value(self):
    """
    returns float with current transmission for 3rd harmonic. (for the energy previously set)
    """
    return self.get_par('T3rd')

  def getT1value(self):
    """
    returns float with current transmission for 3rd harmonic. (for the energy previously set)
    """
    return self.get_par('T1st')

  def getTvalue(self, use3rd=False):
    """
    returns float with current transmission. (for the energy previously set)
    """
    if use3rd:
      return self.getT3value()
    else:
      return self.getT1value()

  def setE(self, E=None, use3rd=False):
    """ set the energy (in keV) for calculation of transmission
        if called without parameter, it reads the value from the
        machine """
    if ( E is None ):
      self.put_par("Eget", "1 second", wait=True)
      # wait for the changes to propogate through the sequence
      self.wait_par('EU1st')
      self.wait_par('E1st')
      self.use3rd = False
      logprint("lusiatt: setting energy for transmission calculation to %.3f keV" % self.__E)
      return self.__E
    else:
      if use3rd:
        self.__E3 = E
      else:
        self.__E = E
      logprint("lusiatt: setting energy for transmission calculation to %.3f keV" % E)
      return E

  def getInOut(self):
    s_title = "filter# |"
    s_in    = " IN     |"
    s_out   = " OUT    |"
    for i, filt in enumerate(self.filters):
      status = filt.state()
      stuck = filt.stuck()
      s_title += "%d|" % i
      if status==Filter.IN:
        if stuck==Filter.NOT_STUCK:
          s_in += estr("X",color="green",type="normal")+"|"
        else:
          s_in += estr("S",color="red",type="normal")+"|"
        s_out+=" |"
      elif status==Filter.OUT:
        if stuck==Filter.NOT_STUCK:
          s_out += estr("X",color="green",type="normal")+"|"
        else:
          s_out += estr("S",color="red",type="normal")+"|"
        s_in+=" |"
      else:
        s_in += estr("?",color="yellow",type="normal")+"|"
        s_out+= estr("?",color="yellow",type="normal")+"|"
    return s_title, s_in, s_out

  def getT(self, printit=False):
    """ Check which filters are `in` and calculate the transmission
        for the energy defined with the `setE` command
        The finding is returned as dictionary """
    self.wait()
    ret = {}
    ret['1st'] = self.getT1value()
    ret['3rd'] = self.getT3value()
    ret['E'] = self.__E
    ret['E3'] = self.__E3
    if printit:
      printnow(self.status())
    return ret

  def setTfast(self, transmission, wait=False, E=None, printit=False, use3rd=False, checkSide=False):
    """ Determines which filters have to be moved in othe beam to
        achieve a transmission as close as possible to the requested one.
        Moves all attenuator blades that will move simultaneously.
  Note : the function moves the filters
  Note2: use the `setE` command before to choose which energy 
         to use for calculation"""
    orig_mode = self.get_par('Mode')
    self.put_par('Mode', 'Fast', wait=True)
    try:
      self.setT(transmission, wait, E, printit, use3rd, checkSide)
    finally:
      # restore original movement mode
      self.put_par('Mode', orig_mode, wait=True)

  def setT(self, transmission, wait=False, E=None, printit=False, use3rd=False, checkSide=False):
    """ Determines which filters have to be moved in othe beam to
        achieve a transmission as close as possible to the requested one.
  Note : the function moves the filters
  Note2: use the `setE` command before to choose which energy 
         to use for calculation"""
    # Check the status of the attenuator
    stat = self.get_par('Status')
    if stat != 'OK':
      warn_str = 'The attenuator is not ready - status is ' + str(stat)
      printnow(warn_str)
      return
    if E is not None:
      self.setE(E, use3rd=use3rd)
    elif self.get_par('Eget') == 'Passive' and (abs(self.get_par('E1st') - Pv.get('SIOC:SYS0:ML00:AO627') ) > 0.010):
      printnow('The current set energy for the fundamental (%.5f) is not the beam energy (%.5f).' %(self.get_par('E1st'), Pv.get('SIOC:SYS0:ML00:AO627') ))
      if raw_input('Is that intended? (y/n)\n') is 'n':
        self.setE()

    if use3rd:
      self.put_par('Td3rd', transmission, wait=True)
      time.sleep(0.1)
      self.wait_par('CalcPend', 'No') # wait for T_CALC record to process
      floor = self.get_par('T3rd_f')
      ceiling = self.get_par('T3rd_c')
    else:
      self.put_par('Td1st', transmission, wait=True)
      time.sleep(0.1)
      self.wait_par('CalcPend', 'No') # wait for T_CALC record to process
      floor = self.get_par('T1st_f')
      ceiling = self.get_par('T1st_c')
    if printit or checkSide:
      printnow('Possible transmissions are: %.5f (floor) and %.5f (ceiling).' %(floor, ceiling))

    if checkSide:
      if raw_input('Use ceiling or floor? (c/f)\n') is 'c':
        self.put_par('Go', 3)
        tval = ceiling
      else:
        self.put_par('Go', 2)
        tval = floor
    else:
      if abs(floor - transmission) >= abs(ceiling - transmission):
        self.put_par('Go', 3)
        tval = ceiling
      else:
        self.put_par('Go', 2)
        tval = floor

    # wait for put to happen
    time.sleep(0.1)

    if wait:
      self.wait()
      if use3rd:
        self.wait_par('E3rd') # wait for T_CALC record to process
        tval = self.getT3value()
      else:
        self.wait_par('E1st') # wait for T_CALC record to process
        tval = self.getT1value()

    if printit or (transmission != 0 and abs((tval-transmission)/transmission)>0.1):
        printnow('Closest possible transmission of %.3f has been applied\n'%(tval))

    return tval

  def edm_control(self):
    """Open the att screen"""
    hutch = self.PVbase.split(":")[0]
    edm_hutch_open("lusiAttScreens/lusiAtt_free.edl", HUTCH=hutch,ATT=hutch)

  def edm_filter_expert(self, num):
    """Show motor expert screen for filter num (0, 1, 2, etc.)."""
    try:
        filter = self.filters[num]
    except:
        print "Filter index out of range!"
        return
    motor = Motor(filter.motorpv)
    motor.expert_screen()

  def status(self):
    s_title,s_in,s_out = self.getInOut()
    s =  "Transmission for 1st harmonic (E=%.2f keV): %.3e\n" % (self.__E,self.getT1value())
    s += "Transmission for 3rd harmonic (E=%.2f keV): %.3e\n" % (self.__E3,self.getT3value())
    sret = s_title + "\n" + s_out + "\n" + s_in + "\n" + s
    return sret

  def __repr__(self):
    return self.status()

  def __call__(self, value, **kw):
    """Shortcut to set the attenuation"""
    self.setT(value, **kw)
