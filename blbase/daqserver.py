import os
import sys
import time
import socket
import pydaq
import Queue
import logging
import argparse
import datetime
import threading
import simplejson as json
from logging.handlers import RotatingFileHandler
from pcaspy import SimpleServer, Driver, Severity, Alarm


LOG = logging.getLogger('daq_ioc')
## LOGGING SETTINGS ##
MAX_BYTES = 104857600
BACKUP_COUNT = 5
FMT_STR = '[ %(asctime)s | %(levelname)-8s] %(message)s'
# IOC Settings
IOC_DATA = '/reg/d/iocData'

pvlabels    = [ ('CPV:STR_DESC:%02d'%i, 'CPV:STR_VAL:%02d'%i) for i in range(1,4) ]
pvcontrols  = [ ('CPV:NUM_DESC:%02d'%i, 'CPV:NUM_VAL:%02d'%i) for i in range(1,4) ]

ioc_pvdb = {
    'HEARTBEAT' : {
        'type' : 'int',
        'scan' : 1,
        'readonly' : True,
    },
    'TOD' : {
        'type' : 'string',
        'scan' : 1,
        'readonly' : True,
    },
    'STARTTOD' : {
        'type' : 'string',
        'readonly' : True,
    },
    'SYSRESET' : {
        'type' : 'int',
    },
}

pvdb = {
    'BEGIN' : {
        'type' : 'enum',
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'STOP' : {
        'type' : 'enum',
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'CONF' : {
        'type': 'enum',
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'STATUS' : {
        'type': 'enum',
        'enums': ['STOPPED', 'FREERUN', 'FIXEDRUN'],
        'readonly' : True,
    },
    'STATE' : {
        'type': 'enum',
        'enums': ['Disconnected', 'Connected', 'Configured', 'Open', 'Running', 'Unknown'],
        'readonly' : True,
    },
    'WAIT' : {
        'type': 'enum',
        'enums': ['NO', 'YES'],
        'readonly' : True,
    },
    'ENDRUN' : {
        'type': 'enum', 
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'DCONNECT' : {
        'type': 'enum',
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'RECORD' : {
        'type': 'enum', 
        'enums': ['NO', 'YES', 'GUI'],
        'value': 2,
        'autosave' : True,
        'config' : True,
    },
    'RESET' : {
        'type': 'enum',
        'enums': ['NO', 'YES'],
        'daqcmd' : True,
    },
    'NEVT' : {
        'type': 'int',
        'value': 0,
        'autosave' : True,
        'config' : True,
    },
    'EVTNUM' : {
        'type': 'int',
        'value': -1,
        'readonly' : True,
    },
    'RUNNUM' : {
        'type': 'int',
        'value': 0,
        'readonly' : True,
    },
    'HOST' : {
        'type' : 'string',
        'autosave' : True,
    },
    'PLATFORM' : {
        'type': 'int',
        'lolim': 0,
        'autosave' : True,
    },
}

def _parse_cli():
    default_host = socket.gethostname()
    default_platform = 0
    default_log = 'INFO'

    parser = argparse.ArgumentParser(
        description='DAQ Control IOC application'
    )

    parser.add_argument(
        'prefix',
        metavar='PV_PREFIX',
        help='The PV prefix to use for the IOC'
    )

    parser.add_argument(
        'ioc_prefix',
        metavar='IOC_PREFIX',
        nargs='?',
        help='The IOC PV prefix to use for the IOC (optional)'
    )

    parser.add_argument(
        '-H',
        '--host',
        metavar='HOSTNAME',
        default=default_host,
        help='The hostname of the server running the DAQ if not using autosave (default: %s)'%default_host   
    )

    parser.add_argument(
        '-p',
        '--platform',
        metavar='PLATFORM',
        type=int,
        default=default_platform,
        help='The platform number of the DAQ if not using autosave (default: %d)'%default_platform
    )

    parser.add_argument(
        '-n',
        '--name',
        metavar='IOC_NAME',
        default=None,
        help='The name of the IOC instance - this is needed for autosave (default: None)'
    )

    parser.add_argument(
        '--log-level',
        metavar='LOG_LEVEL',
        default=default_log,
        help='the logging level of the client (default %s)'%default_log
    )

    parser.add_argument(
        '--log-file',
        metavar='LOG_FILE',
        help='an optional file to write the log output to'
    )

    return parser.parse_args()


class IocAdmin(object):
    def __init__(self, name, prefix, driver):
        self.run = True
        self.name = name
        self.prefix = prefix
        self.pvdb = ioc_pvdb
        self.driver = driver
        self.autosave = (name is not None)
        self.refresh = 5.0
        self.nSaved = 8
        self.type_map = {
            int   : "int",
            long  : "int",
            str   : "string",
            float : "float"
        }
        if self.autosave:
            LOG.info('Initializng autosave and restoring values')
            self.savereq = self.make_autosave_reqs()
            self.make_autosave_dir()
            if not self.load_values():
                LOG.error('Problem loading autosave file!')
            self.set_autosave_file()
            self.remove_oldest_file()
            self.make_pv_list()
        else:
            LOG.debug('Autosave not active - using passed parameters for host and platform')
        for pv in self.pvdb.keys():
            # remove the invalid state
            self.driver.setParamStatus(pv, Alarm.NO_ALARM, Severity.NO_ALARM)
        # Set up the IOC pvs
        self.start_int = int(time.time())
        self.start_str = self.tod()
        # start autosave thread if autosave is enabled
        if self.autosave:
            LOG.debug('Starting autosave thread')
            self.ioc_id = threading.Thread(target = self.runAuto)
            self.ioc_id.setDaemon(True)
            self.ioc_id.start()

    def date_str(self, dt):
        """Return a string representing a date from a datetime object."""
        return "{0:02}/{1:02}/{2:04} {3:02}:{4:02}:{5:02}".format(
                dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second)

    def tod(self):
        """Return the current time of day on this machine."""
        dt = datetime.datetime.now()
        return self.date_str(dt)

    def heartbeat(self):
        """Return the number of seconds this IOC has been running."""
        return int(time.time()) - self.start_int

    def starttod(self):
        """Return the time of day this IOC was last rebooted."""
        return self.start_str

    def pv_list_lines(self, prefix, d):
        """Helper function to get the lines for the IOC.pvlist file in make_pv_list."""
        lines = []
        for key, value in d.items():
            tp = value["type"]
            if tp == "int":
                epics_type = "longout"
            elif tp == "float":
                epics_type = "ao"
            else:
                epics_type = "stringout"
            PV = prefix + key
            lines.append("{0}, {1}".format(PV, epics_type))
        return lines

    def make_pv_list(self):
        """Writes the IOC.pvlist file in the iocInfo directory."""
        if self.name:
            file = "{0}/{1}/iocInfo/IOC.pvlist".format(IOC_DATA, self.name)
            lines = self.pv_list_lines(self.driver.prefix, self.driver.pvdb)
            ioc_lines = self.pv_list_lines(self.prefix, self.pvdb)
            try:
                all_lines = lines + ioc_lines
                with open(file, "w") as f:
                    for line in all_lines:
                        f.write(line + "\n")
            except StandardError as e:
                print "Error writing pv list. {0}".format(e)

    def make_autosave_reqs(self):
        LOG.debug('Deteriming autosave request list')
        reqs = []
        for key, value in self.driver.pvdb.iteritems():
            if value.get('autosave', False):
                LOG.debug('Found autosave request for %s%s', self.driver.prefix, key)
                reqs.append(key)
        LOG.debug('Found autosave requests for %d PVs', len(reqs))
        return reqs

    def make_autosave_dir(self):
        """Makes the autsave directory if it does not exist."""
        if self.name:
           self.my_dir = IOC_DATA + "/{0}/autosave".format(self.name)
        else:
            self.my_dir = "autosave_" + self.prefix.replace(":", "_").lower()
            if not os.path.exists(self.my_dir):
                os.mkdir(self.my_dir)
            elif not os.path.isdir(self.my_dir):
                raise IOError("Filename conflict for autosave directory")
        LOG.debug('Autosave directory: %s', self.my_dir)

    def set_autosave_file(self):
        """Picks a name for the autosave file."""
        date_string = str(datetime.datetime.now())
        valid_filename = date_string.replace(" ", "_").replace(":", "")
        truncated = valid_filename.split(".")[0]
        self.filename = "{0}/{1}.txt".format(self.my_dir, truncated)
        LOG.debug('Current autosave file: %s', self.filename)

    def save_values(self):
        """Serializes all values into a JSON object."""
        try:
            LOG.debug('Starting autosave update')
            value_dict = {}
            for reason in self.savereq:
                value_dict[reason] = self.driver.getParam(reason)
            with open(self.filename, "w") as f:
                f.write(json.dumps(value_dict, sort_keys = True, indent = "  ") + "\n")
            LOG.debug('Autosave update completed')
        except StandardError as e:
            LOG.error('Autosave error: %s', e)

    def load_values(self, i=-1):
        """Loads all values from the most recent JSON serialization."""
        save_files = self.list_autosaves()
        if len(save_files) == 0:
            return False
        most_recent = save_files[i]
        try:
            LOG.debug("Opening autosave file: %s/%s", self.my_dir, most_recent)
            with open("{0}/{1}".format(self.my_dir, most_recent), "r") as f:
                value_dict = json.load(f)
            loaded_something = False
            loaded_count = 0
            for reason, value in value_dict.items():
                try:
                    expected_type = self.driver.pvdb[reason]["type"]
                    value_type = self.type_map[type(value)]
                    if value_type == expected_type or (expected_type == 'enum' and value_type == 'int'):
                        self.driver.setParam(reason, value)
                        loaded_count += 1
                        loaded_something = True
                        LOG.debug('Autosave restored %s to a value of %s', reason, value)
                    else:
                        error = "Saved value for {} is type ".format(reason)
                        error += "{} instead of expected ".format(value_type)
                        error += "type {}. Skipping...".format(expected_type)
                        raise TypeError(error)
                except Exception as exc:
                    LOG.error('Could not load value for %s. %s', reason, exc)
            LOG.info('Autosave restored %d of %d values', loaded_count, len(self.savereq))
            did_work = loaded_something
            if not did_work:
                raise IOError('All values in autosave were invalid.')
        except Exception as exc:
            LOG.error('Could not load values. %s', exc)
            if abs(i) >= len(save_files):
                LOG.warning('No more valid files to load.')
                did_work = False
            else:
                LOG.warning('Trying older autosave...')
                did_work = self.load_values(i-1)
        return did_work

    def list_autosaves(self):
        """Returns a list of files in the autosave folder."""
        flist = [f for f in os.listdir(self.my_dir)
                if os.path.isfile("{0}/{1}".format(self.my_dir, f))]
        flist.sort()
        return flist

    def remove_oldest_file(self):
        """Removes old autosaves until we have the max number of files."""
        save_files = self.list_autosaves()
        while len(save_files) > self.nSaved:
            oldest = save_files[0]
            LOG.debug("Removing old autosave file: %s/%s", self.my_dir, oldest)
            os.remove("{0}/{1}".format(self.my_dir, oldest))
            save_files = self.list_autosaves()

    def shutdown(self):
        if self.autosave: 
            LOG.debug('Autosave shutdown requested')
            self.run = False
            self.ioc_id.join()

    def runAuto(self):
        while self.run:
            time.sleep(self.refresh)
            self.save_values()
        LOG.debug('Autosave thread exitting...')


class DaqDriver(Driver):
    def __init__(self, host, platform, prefix, ioc_prefix, ioc_name):
        super(DaqDriver, self).__init__()
        self.run = True
        self.connected = False
        self.prefix = prefix
        self.pvdb = pvdb
        self.setParam('HOST', host)
        self.setParam('PLATFORM', platform)
        self.ioc = IocAdmin(ioc_name, ioc_prefix, self)
        self.host = self.getParam('HOST')
        self.platform = self.getParam('PLATFORM')
        self.confpv = self.get_tagged_pvs('config')
        self.readonly = self.get_tagged_pvs('readonly')
        self.cmds = self.get_tagged_pvs('daqcmd')
        self.daq = self.daq = pydaq.Control(host=self.host, platform=self.platform)
        self.refresh = 1.0
        for pv in self.pvdb.keys():
            # remove the invalid state
            self.setParamStatus(pv, Alarm.NO_ALARM, Severity.NO_ALARM)
        self.eid = Queue.Queue()
        self.sig = threading.Event()
        self.lock = threading.Lock()
        self.lock.acquire()
        self.tid = threading.Thread(target = self.runDAQ)
        self.tid.setDaemon(True)
        self.tid.start()
        self.nid = threading.Thread(target = self.runNumEvent)
        self.nid.setDaemon(True)
        self.nid.start()

    def _reinit_pydaq(self):
        del self.daq
        self.daq = pydaq.Control(host=self.host, platform=self.platform)

    def read(self, reason):
        if hasattr(self.ioc, reason.lower()):
            return getattr(self.ioc, reason.lower())()
        else:
            return self.getParam(reason)

    def write(self, reason, value):
        status = True
        # take proper actions
        if reason == 'HOST':
            if self.ioc.name is None:
                LOG.warn("Hostname PV cannot be changed at runtime!")
                status = False
            elif value != self.getParam('HOST'):
                LOG.info("Changing the DAQ host to %s", value)
                if self.daq is not None:
                    self.disconnect()
                    self._reinit_pydaq()
        elif reason == 'PLATFORM':
            if self.ioc.name is None:
                LOG.warn("Platform PV cannot be changed at runtime!")
                status = False
            elif value != self.getParam('PLATFORM'):
                LOG.info("Changing the DAQ platform to %d", value)
                if self.daq is not None:
                    self.disconnect()
                    self._reinit_pydaq()
        elif reason in self.cmds:
            if value == 1:
                self.eid.put(reason)
            else:
                status = False
        elif reason in self.readonly:
            LOG.warn("The %s PV is read-only!", reason)
            status = False
        elif reason in self.confpv:
            # signal if a configuration PV has changed
            if value != self.getParam(reason):
                self.sig.set()
        elif reason == 'SYSRESET':
            # the IOC should exit now
            self.run = False

        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def get_tagged_pvs(self, tag):
        tagged = []
        # main db
        for key, value in self.pvdb.iteritems():
            if value.get(tag, False):
                tagged.append(key)
        # iocAdmin db
        for key, value in self.ioc.pvdb.iteritems():
            if value.get(tag, False):
                tagged.append(key)
        return tagged

    def get_info_list(self, info_type):
        info_list = []
        for descpv, valpv in info_type:
            tdesc = self.getParam(descpv)
            if tdesc:
                tval = self.getParam(valpv)
                info_list.append((tdesc,tval))
        return info_list

    def get_record(self):
        if self.getParam('RECORD') == 0:
            LOG.info("Record is set to False")
            return False
        elif self.getParam('RECORD') == 1:
            LOG.info("Record is set to True")
            return True
        else:
            LOG.info('Record is what you set in GUI')
            return None 

    def wait(self, active):
        if active:
            if self.getParam('WAIT') != 1:
                self.setParam('WAIT', 1)
                self.updatePVs()
        else:
            self.setParam('WAIT', 0)

    def state(self):
        if hasattr(self.daq, 'state'):
            return self.daq.state()
        else:
            return 6

    def connect(self):
        if not self.connected:
            LOG.debug('Connecting to the DAQ on %s, platform %d',self.host,self.platform)
            self.daq.connect()
            self.connected = True
            LOG.debug('DAQ connection attempt successful')
            return True
        elif self.state() == 0:
            LOG.info('DAQ connection was closed on the remote end - will need to reinit!')
            self.cleanup()
            LOG.debug('Connecting to the DAQ on %s, platform %d',self.host,self.platform)
            self.daq.connect()
            self.connected = True
            LOG.debug('DAQ connection attempt successful')
            return True
        else:
            LOG.debug('Already connected to the DAQ on %s, platform %d',self.host,self.platform)
            return False

    def start(self):
        nshots = self.getParam('NEVT')
        labels=self.get_info_list(pvlabels)
        controls=self.get_info_list(pvcontrols)
        record=self.get_record()
        if self.connect() or self.sig.is_set():
            LOG.info('Begin Configure %7s events', nshots)
            self.daq.configure(events=nshots,controls=controls,labels=labels,record=record)
            self.sig.clear()
        LOG.info('Begin CalibCycle %7s events', nshots)
        self.daq.begin(events=nshots,controls=controls,labels=labels)
        self.wait(True)
        LOG.debug('ControlPVs: %s', controls)
        LOG.debug('Labels: %s', labels)
        if nshots:
            self.setParam('STATE', self.state())
            self.setParam('STATUS', 2)
            self.updatePVs()
            self.daq.end()
            self.setParam('STATE', self.state())
            self.setParam('STATUS', 0)
            self.wait(False)
            LOG.info('Finished CalibCycle')
            self.setParam('EVTNUM', self.daq.eventnum())
            self.setParam('RUNNUM', self.daq.runnumber())
        else:
            self.setParam('STATE', self.state())
            self.setParam('STATUS', 1)
            self.lock.release()

    def stop(self):
        self.lock.acquire()
        self.daq.stop()
        self.setParam('STOP', 0)
        self.setParam('STATE', self.state())
        self.setParam('STATUS', 0)
        self.wait(False)
        LOG.info('Finished CalibCycle')
        self.setParam('EVTNUM', self.daq.eventnum())
        self.setParam('RUNNUM', self.daq.runnumber())

    def configure(self):
        nshots = self.getParam('NEVT')
        labels=self.get_info_list(pvlabels)
        controls=self.get_info_list(pvcontrols)
        record=self.get_record()
        self.wait(True)
        self.connect()
        LOG.info('Begin Configure %7s events', nshots)
        self.daq.configure(events=nshots,controls=controls,labels=labels,record=record)
        self.sig.clear()
        self.wait(False)

    def endrun(self):
        self.wait(True)
        self.daq.endrun()
        self.setParam('STATE', self.state())
        self.setParam('STATUS', 0)
        self.wait(False)
        if self.getParam('RUNNUM') == 0:
            LOG.info('Ending unsaved run')
        else:
            LOG.info('Ending run %s', self.getParam('RUNNUM'))

    def disconnect(self):
        self.wait(True)
        self.daq.disconnect()
        self.connected = False
        self.wait(False)
        if self.getParam('RUNNUM') == 0:
            LOG.info('Disconnect from unsaved run')
        else:
            LOG.info('Disconnect from run %s', self.getParam('RUNNUM'))

    def cleanup(self):
        LOG.debug('Cleaning up DAQ state')
        self._reinit_pydaq()
        self.connected = False
        LOG.debug('Destroyed and recreated pydaq Control object')
        if self.getParam('STATUS') == 1:
            LOG.debug('DAQ is in freerun - attempting to stop event number polling')
            if not self.lock.acquire(False):
                # a bit ugly but oh well...
                LOG.debug('Restarting event poller thread')
                self.nid = threading.Thread(target = self.runNumEvent)
                self.nid.setDaemon(True)
                self.nid.start()
            LOG.debug('Stopped event number polling')
        self.setParam('STATE', self.state())
        self.setParam('STATUS', 0)
        LOG.debug('Set DAQ status to \'STOPPED\'')
        self.wait(False)
        LOG.debug('Cleared DAQ \'WAIT\' PV')
        self.connected = False

    def runNumEvent(self):
        while True:
            with self.lock:
                self.setParam('EVTNUM', self.daq.eventnum())
                self.updatePVs()
            time.sleep(self.refresh)

    def runDAQ(self):
        while True:
            try:
                cmd = self.eid.get()
                if cmd == 'BEGIN':
                    if self.getParam('STATUS') != 0:
                        LOG.debug('DAQ is already running ignoring begin command!')
                    else:
                        self.start()
                elif cmd == 'STOP':
                    if self.getParam('STATUS') != 1:
                        LOG.warn('DAQ is not free running ignoring stop command!')
                    else:
                        self.stop()
                elif cmd == 'CONF':
                    if self.getParam('STATUS') != 0:
                        LOG.debug('DAQ is currently running ignoring configure command!')
                    else:
                        self.configure()
                elif cmd == 'ENDRUN':
                    if self.getParam('STATUS') == 0:
                        self.endrun()
                    elif self.getParam('STATUS') == 1:
                        # if the DAQ is free-running try to stop it first
                        self.stop()
                        self.endrun()
                    else:
                        LOG.warn('DAQ is currently running ignoring endrun command!')
                elif cmd == 'DCONNECT':
                    if self.getParam('STATUS') == 0:
                        self.disconnect()
                    elif self.getParam('STATUS') == 1:
                        # if the DAQ is free-running try to stop it first
                        self.stop()
                        self.disconnect()
                    else:
                        LOG.warn('DAQ is currently running ignoring disconnect command!')
                elif cmd == 'RESET':
                    LOG.info('Restart of the pydaq control connection has been requested')
                    self.cleanup()
                    LOG.info('Existing pydaq control connection has be released')
                else:
                    LOG.error("Unsupported DAQ epics cmd: %s!", cmd)

                # Aknowledge command is being processed
                self.setParam(cmd, 0)
                self.updatePVs()
            except RuntimeError as daq_err:
                LOG.error("A runtime error has been encountered in pydaq: %s", daq_err)
                LOG.error("Attempting to cleanup existing session")
                self.cleanup()

def execute(prefix, host, platform, ioc_prefix=None, ioc_name=None, log_level=logging.INFO):
    """
    Starts a server which hosts PVs for controlling the DAQ instance specified via
    host and platform.

    Params:
    - prefix:       The base name used for the PVs hosted by this server.
    - host:         The hostname or ip of the machine hosting the control_gui process of
                    the DAQ instance you wish to control.
    - platform:     The platform number used by the DAQ instance you wish to control.
    - ioc_prefix:   The optional prefix to use for the IOC admin PVs. If not specified
                    the normal prefix is used.
    - ioc_name:     The name of the this IOC in the IOC_DATA directory. Needs to be
                    specified to use autosave.
    - log_level:    The log level to be used for the server. Defaults to logging.INFO. 
    """
    if not prefix.endswith(':'):
        prefix = prefix + ':'

    LOG.setLevel(log_level)

    return _execute(prefix, host, platform, ioc_prefix, ioc_name)


def _execute(prefix, host, platform, ioc_name=None, ioc_prefix=None):
    for descpv, valpv in pvlabels:
        pvdb[descpv] = {'type': 'string'}
        pvdb[valpv] = {'type': 'string'}
    for descpv, valpv in pvcontrols:
        pvdb[descpv] = {'type': 'string'}
        pvdb[valpv] = {'type': 'float', 'prec': 3}
    # If no IOC prefix is given just use the base prefix
    if ioc_prefix is None:
        ioc_prefix = prefix

    LOG.info('Starting DAQ server, abort with Ctrl-C')
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    server.createPV(ioc_prefix, ioc_pvdb)
    driver = DaqDriver(host, platform, prefix, ioc_prefix, ioc_name)
    LOG.debug('DAQ server is now started')
    try:
        # Run the driver process loop
        while driver.run:
            try:
                # process CA transactions
                server.process(0.1)
            except KeyboardInterrupt:
                LOG.info('DAQ server stopped by console interrupt!')
                driver.run = False
    finally:
        # do a final autosave
        driver.ioc.shutdown()

    # If we get here the server died in an unexpected way
    if driver.run:
        LOG.error('DAQ server exited unexpectedly!')
        return 1
    else:
        LOG.info('DAQ server exited normally')
        return 0

def _check_prefix(prefix):
    if prefix is None:
        return prefix
    else:
        if prefix.endswith(':'):
            return prefix
        else:
            return prefix + ':'

if __name__ == '__main__':
    args = _parse_cli()
    prefix = _check_prefix(args.prefix)
    ioc_prefix = _check_prefix(args.ioc_prefix)
    
    # Setup up the logging client
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(format=FMT_STR, level=log_level)
    if args.log_file is not None:
        log_fmt = logging.Formatter(FMT_STR)
        file_handler = RotatingFileHandler(args.log_file, MAX_BYTES, BACKUP_COUNT)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_fmt)
        LOG.addHandler(file_handler)

    sys.exit(_execute(prefix, args.host, args.platform, args.name, ioc_prefix))
