from copy import deepcopy
from types import MethodType
from datetime import datetime
import pycdb
dbpath = "/reg/g/pcds/dist/pds/{0}/misc/.configdbrc"

class DaqConfig(object):
    """
    Generic container to hold daq config devices in one place.
    """
    def __init__(self, **daq_config_devices):
        """
        Initialize by inputting the Dcfg objects to be used.
        Example: DaqConfig(acqiris=Acqiris("xpp","BEAM"), evr=...)
        """
        for name, obj in daq_config_devices.items():
            setattr(self, name, obj)

class UserInterface(object):
    """
    Class that defines a common interface for various objects in this class.
    """
    def __init__(self):
        self._option_map = {}
        self._methods = []

    def show_all(self, live=False):
        """Print all values in a nice table."""
        table = [[],[]]
        for name, keys in self._methods:
            val = self._get(live, *keys)
            val = self._opt_get_val(val, name)
            table[0].append(name)
            table[1].append(val)
        print_table(table)        

    def diff(self):
        """
        Print differences between live and local values in a nice table.
        Return the number of differences.
        """
        diff_count = 0
        table = [["Field"],["Local"],["Live"]]
        for name, keys in self._methods:
            live_val = self._get(True, *keys)
            curr_val = self._get(False, *keys)
            if live_val != curr_val:
                diff_count += 1
                table[0].append(name)
                table[1].append(curr_val)
                table[2].append(live_val)
        if diff_count > 0:
            print_table(table)
        return diff_count

    def _make_get(self, name, *keys):
        """Return a specific get function to be added in _add_methods"""
        def get(self, live=False):
           """
           Get the local or live value.
           """
           val = self._get(live, *keys)
           return self._opt_get_val(val, name)
        return get

    def _make_set(self, name, *keys):
        """Return a specific set function to be added in _add_methods"""
        def set(self, val=None, commit=False):
            """
            Set the local value.
            This will need to be committed before it can take effect. You can
            commit all changes by using commit=True in a set command or by
            calling .commit()
            """
            val = self._opt_set_val(val, name)
            if val is None:
                print "No valid value found"
                return
            self._set(val, commit, *keys)
        return set 

    def _add_methods(self, name, *keys):
        """
        Adds database get and set methods to this object. Methods will be
        named like get_name and they will access the loaded configuration
        dictionary using their keys in order on the nested dictionaries.

        Names that begin with a leading underscore as "_name" will cause
        pseudo-private methods to be created instead.
        """
        name = name.lower()
        if name[0] == "_":
            bindMethod(self, "_get{0}".format(name), self._make_get(name, *keys))
            bindMethod(self, "_set{0}".format(name), self._make_set(name, *keys))
        else:
            bindMethod(self, "get_{0}".format(name), self._make_get(name, *keys))
            bindMethod(self, "set_{0}".format(name), self._make_set(name, *keys))
            self._register(name, *keys)

    def _register(self, name, *keys):
        """
        Method to give _add_methods additional setup tasks on adding a method.
        """
        self._methods.append((name, keys))

    def _add_options(self, name, *options):
        """
        Adds text options for configuration fields that are stored as integers
        but understood as enums. Options should be the enum strings in order.
        """
        array = []
        for opt in options:
            array.append(opt)
        self._option_map[name] = array

    def _opt_get_val(self, val, name):
        """If name has options, convert val to the correct option."""
        try:
            return self._option_map[name][int(val)]
        except:
            return val

    def _opt_set_val(self, val, name):
        """
        If name has options, allow val to be set as integer option, string
        option, or choose val from a prompt. Returns None is val is invalid
        or if prompt is aborted, otherwise returns val to be set.
        """
        if name in self._option_map:
            if val is None:
                val = self._opt_prompt(name)
            elif type(val) == int:
                if val >= len(self._option_map[name]):
                    val = None
            elif type(val) == str:
                try:
                    val = self._option_map[name].index(val)
                except:
                    val = None
            else:
                val = None
        return val

    def _opt_prompt(self, name):
        """Provides an interface for the user to select an enum option."""
        print "Options for {0}".format(name)
        for i, opt in enumerate(self._option_map[name]):
            print "{0}: {1}".format(i, opt)
        choice = raw_input("Choose an option or x to abort:\n")
        try:
            if choice in self._option_map[name] or int(choice) in range(i):
                return choice
            else:
                print "Set aborted."
        except:
            print "Set aborted."

    def _add_enum(self, name, enum_name):
        """
        Adds options based on the defined enums.
        name is the name set in _add_method
        enum_name is the entry in get_enums
        """
        enums = self._get_enums()[enum_name]
        options = [""] * len(enums)
        for enum_string, value in enums.items():
            options[value] = enum_string
        self._add_options(name, *options)

class Dcfg(UserInterface):
    """
    Daq config device. Contains functions that a device should have to
    interface with pycdb and change its daq settings. Provides a way to
    set up these objects programatically by inheriting from this object
    and calling key methods:

    ._add_methods(name, *keys)
    ._add_subcfg(subcfg, name)
    ._add_options(name, *options)
    ._add_enum(name, enum_name)
    """
    def __init__(self, hutch, *aliases, **kwargs):
        """
        hutch is the 3 letter xpp, xcs, etc.
        *aliases are the configdb profiles to sync with this object (min 1)
        **kwargs has two options:
          typeid: the config typeid in configdb
          src: the device id in configdb
        The database will be queried with these search terms, and the first
        xtc object found will be used. You should supply enough information
        to narrow down the search to one xtc object.
        """
        if len(aliases) == 0:
            raise AttributeError("Object needs at least one alias to access daq config database.")
        self.hutch = hutch
        self.aliases = aliases
        self._db = None
        self._dcurr = None
        self._xtc_cache = None
        self._cache_time = None
        self._typeid = kwargs.get("typeid", None)
        self._src = kwargs.get("src", None)
        self._keyNameMap = {}
        self._subcfgs = []
        UserInterface.__init__(self)

    def show_all(self, live=False):
        """
        View the current (not committed) local configuration. If no local
        configuration exists, view the live configuration instead. If argument
        live=True, then view the live configuration regardless.
        """
        if live == False and self._dcurr is None:
            live = True
            print "No local configuration. Checking live instead...\n"
        print type(self).__name__.title() + ":"
        UserInterface.show_all(self, live)
        for subcfg, name in self._subcfgs:
            print "\n" + name.title() + ":"
            subcfg.show_all(live)

    def diff(self):
        """
        Prints differences between the stored configuration dictionary and the
        live configuration dictionary. Returns the number of differences.
        """
        if self._dcurr is None:
            print "No changes made."
            return 0
        else:
            print type(self).__name__.title() + ":"
            nDiff = UserInterface.diff(self)
            for subcfg, name in self._subcfgs:
                print name.title() + ":"
                nDiff += subcfg.diff()
            if nDiff == 0:
                print "No differences found."
            return nDiff

    def _register(self, name, *keys):
        """Set up keyNameMap in addition to normal _register."""
        self._keyNameMap[str(keys)] = name
        UserInterface._register(self, name, *keys)

    def _get(self, live, *keys):
        """Extract the value from nested dictionaries using *keys."""
        if live or self._dcurr is None:
            d = self.cfg_dict_get()
        else:
            d = self._dcurr
        if d is not None:
            return nested_dict_get(d, *keys) 

    def _set(self, val, commit, *keys):
        """Sets the value to nested local dictionary using *keys."""
        if self._dcurr is None:
            self._load()
        if self._dcurr is not None:
            nested_dict_set(self._dcurr, val, *keys)
            if commit:
                self.commit()

    def _get_enums(self):
        """Return an enums dictionary if one was defined, or None"""
        try:
            return self._sync_and_get_xtc()[0].get_enums()
        except:
            return None

    def _add_subcfg(self, subcfg, name):
        """
        Add a subconfig to the list of subconfigs for show_all and diff
        """
        self._subcfgs.append((subcfg, name))

    def commit(self):
        """
        Commits all changes to the database using the local config dictionary.
        """
        if self._dcurr is not None:
            success = self.cfg_dict_set(self._dcurr)
            if success:
                self._dcurr = None
                print "Commit successful."
            else:
                print "Error on config commit."
        else:
            print "Commit aborted, no stored configuarion dictionary."

    def cancel_set(self):
        """Discard all uncommitted changes."""
        self._dcurr = None
        print "Uncommitted changes discarded."

    def database_sync(self):
        """Set the local database to the live config."""
        self._load()

    def check_alias_sync(self, interactive=True):
        """
        Compares the configuration in all aliases. If they do not match, lets
        the user choose which alias's configuration to use to override the
        other configurations.

        To check sync without fixing it, set argument interactive=False.
        """
        nAlias = len(self.aliases)
        if nAlias == 1:
            print "Only one alias: {0}".format(self.aliases[0])
            print "Nothing to sync."
            return True
        cfgDicts = []
        for i in range(nAlias):
            cfgDicts.append(self.cfg_dict_get(i))
        diffLists = dictDiffs(*cfgDicts)
        if len(diffLists) == 0:
            print "Aliases are properly synced!"
            return True
        elif not interactive:
            return False
        else:
            print "Alias differences:"
            printDiffs(diffLists, *self.aliases)
            print "Sync Choices:"
            i = 0
            for alias in self.aliases:
                print "[{0}] : {1}".format(i, alias)
                i += 1
            choice = raw_input("Pick a number to sync to that alias or n to cancel:\n")
            if choice in range(i):
                d = self.cfg_dict_get(i)
                if d is None:
                    success = False
                else:
                    success = self.cfg_dict_set(d)
            else:
                success = False
            if success:
                print "Sync successful."
            else:
                print "Sync failed."
            return success

    def _load(self):
        """Initializes a local configuration dictionary."""
        self._dcurr = self.cfg_dict_get()

    def cfg_dict_get(self, i=0):
        """
        Gets the raw configuration dictionary from pycdb.
        Gets a cached version instead if we've connected very recently.
        """
        ct = self._cache_time
        if ct is None or (datetime.now() - ct).total_seconds() > 5:
            self._xtc_cache = self._sync_and_get_xtc()
            self._cache_time = datetime.now()
        xtc = self._xtc_cache
        if xtc is not None:
            return self._xtc_dot_get_line(xtc[i])

    def _xtc_dot_get_line(self, xtc):
        """
        Correct way to get the config dict from the xtc file, which
        should not change between xtc classes.
        (unfortunately it can and does...)
        """
        return xtc.get()

    def cfg_dict_set(self, d):
        """
        Sets and commits a modified configuration dictionary through pycdb
        """
        xtclist = self._sync_and_get_xtc()
        if xtclist is not None:
            for xtc in xtclist:
                xtc.set(d)
            self._set_xtc_and_commit(xtclist)
            return True
        else:
            return False

    def _get_xtc(self):
        """ Gets one xtc file for each alias from the pycdb.Db object. """
        xtclist = []
        for alias in self.aliases:
            kwargs = {"alias" : alias}
            if self._typeid is not None:
                kwargs["typeid"] = self._typeid
            if self._src is not None:
                kwargs["src"] = self._src
            xtclist.append(self._db.get(**kwargs)[0])
        return xtclist

    def _sync_and_get_xtc(self):
        """
        Connects the pycdb.Db object and calls _get_xtc. Disconnects afterward.
        """
        xtclist = None 
        if self._connect():
            self._db.sync()
            xtclist = self._get_xtc()
            self._disconnect()
        return xtclist

    def _set_xtc_and_commit(self, xtclist):
        """
        Connects the pycdb.Db object and sets all of the values from the xtc
        objects in xtclist. Commits and then disconnects.
        """
        if self._connect():
            for xtc, alias in zip(xtclist, self.aliases):
                self._db.set(xtc, alias)
            self._db.commit()
            self._disconnect()

    def _connect(self):
        """Initializes the pycdb.Db object. If it does not exist."""
        if self._db is None:
            try:
                self._db = pycdb.Db(dbpath.format(self.hutch.lower()))
                return True
            except Exception as e:
                print "Failed to connect to daq config mysql database."
                print e
                return False

    def _disconnect(self):
        """Unlocks and unsets the pycdb.Db object."""
        if self._db is not None:
            self._db.unlock()
            self._db = None


class Subcfg(UserInterface):
    """
    Logical subdivision of a Dcfg.

    Initialize this object in the __init__ statement of your Dcfg object
    and register it by using _add_subcfg.
    """
    def __init__(self, parent_obj, *keys):
        self._parent = parent_obj
        self._keys = keys
        UserInterface.__init__(self)

    def _get_enums(self):
        """Return the enum list from parent."""
        return self._parent._get_enums()

    def commit(self):
        """Commit all changes to the database."""
        self._parent.commit()


class SubcfgDict(Subcfg):
    """
    Logical dictionary subdivision of a Dcfg.
    """
    def _get(self, live, *keys):
        """Call main Dcfg object's _get method appropriately."""
        key_path = self._keys + keys
        return self._parent._get(live, *key_path)

    def _set(self, val, commit, *keys):
        """Call main Dcfg object's _set method appropriately."""
        key_path = self._keys + keys
        self._parent._set(val, commit, *key_path)


class SubcfgList(Subcfg):
    """
    Wrapper for pycdb entries that are lists of identically structured dict

    Latches on to a Dcfg object and provides a submenu for dealing with these
    lists.

    Methods:
    .count()        Returns the number of entries in the list
    .show_all()     Prints all entries in the list as a nice table
    .entry_add()    Add an entry to the list
    .entry_remove() Remove an entry from the list
    .diff()         Show differences between live and stored list
    """
    def __init__(self, parent_obj, *keys):
        """
        parent_obj(Dcfg)    The object that manages the pycdb dictionaries
        *keys(string)       Path of keys from the pycdb dict to this list
        """
        self._headers = [["Index"]]
        self._methods = []
        Subcfg.__init__(self, parent_obj, *keys)

    def show_all(self, live=False):
        """Print all entries in the list as a nice table."""
        data = self._get_all(live)
        print_table(data)

    def _get_all(self, live):
        """Get all entries as an array of arrays."""
        data = deepcopy(self._headers)
        for i in range(self.count(live)):
            data[0].append(i)
            for j, (name, keys) in enumerate(self._methods):
                val = self._get(i, live, *keys)
                val = self._opt_get_val(val, name)
                data[j+1].append(val)
        return data

    def diff(self):
        """Print differences between live and stored list."""
        live_table = self._get_all(True)
        local_table = self._get_all(False)
        live_diff, local_diff = table_diff(live_table, local_table)
        if live_diff is not None and local_diff is not None:
            print "Local:"
            print_table(local_diff)
            print "Live:"
            print_table(live_diff)
            return len(live_diff[0]) - 1
        return 0

    def _make_get(self, name, *keys):
        """
        Return a specific get function to be added in _add_methods
        Unlike the normal _make_get, we need to specify a list index.
        """
        def get(self, index, live=False):
            """Get the local or live value at index."""
            val = self._get(index, live, *keys)
            return self._opt_get_val(val, name)
        return get

    def _make_set(self, name, *keys):
        """
        Return a specific set function to be added in _add_methods
        Unlike the normal _make_set, we need to specify a list index.
        """
        def set(self, index, val=None, commit=False):
            """
            Set the local value at index.
            This will need to be committed before it can take effect. You can
            commit all changes by using commit=True in a set command or by
            calling .commit()
            """
            val = self._opt_set_val(val, name)
            if val is None:
                print "No valid value found."
                return
            self._set(index, val, commit, *keys)
        return set

    def _register(self, name, *keys):
        """In addition to normal _register, build headers for our table."""
        self._headers.append([name.title()])
        Subcfg._register(self, name, *keys)

    def _get(self, index, live, *keys):
        """Call main Dcfg object's _get method appropriately."""
        try:
            key_path = self._keys + (index,) + keys
            return self._parent._get(live, *key_path)
        except IndexError:
            errstr = "Cannot get data from index {}".format(index)
            errstr += ". Out of range."
            print errstr

    def _set(self, index, val, commit, *keys):
        """Call main Dcfg object's _set method appropriately."""
        try:
            key_path = self._keys + (index,) + keys
            self._parent._set(val, commit, *key_path)
        except IndexError:
            errstr = "Cannot set data to index {}".format(index)
            errstr += ". Out of range."
            print errstr

    def count(self, live=False):
        """Return the number of entries in this list."""
        return len(self._parent._get(live, *self._keys))

    def entry_add(self, entry={}, index=None, commit=False):
        """
        Add an entry to the list.

        If the user forgets key fields, prompt for them.
        Place the new entry at the given index, or at the end by default.

        Trust user to not send malicious values. Fields omitted from object
        will take values from first entry in list. List is assumed to be
        non-empty.
        """
        entry_list = self._parent._get(False, *self._keys)
        new_entry = deepcopy(entry_list[0])
        for name, keys in self._methods:
            d = entry
            key_found = True
            for key in keys:
                try:
                    d = d[key]
                except:
                    key_found = False
                    break
            if key_found:
                value = d
            else:
                print "No value found for required field {}".format(name)
                value = raw_input("Please enter a value:\n")
            target_d = new_entry
            for i in range(len(keys) - 1):
                target_d = target_d[keys[i]]
            target_d[keys[-1]] = value
        if index is None:
            entry_list.append(new_entry)
        else:
            entry_list.insert(index, new_entry)
        self._parent._set(entry_list, commit, *self._keys)

    def entry_remove(self, index, commit=False):
        """Remove an entry from the list."""
        entry_list = self._parent._get(False, *self._keys)
        entry_list.pop(index)
        self._parent._set(entry_list, commit, *self._keys)


def bindMethod(obj, methodName, method):
    """Adds method to obj under methodName."""
    setattr(obj, methodName, MethodType(method, obj))

def nested_dict_get(d, *keys):
    """Extract value from nested dictionary d using keys in order."""
    val = d
    for key in keys:
        val = val[key]
    return val

def nested_dict_set(d, val, *keys):
    """Set value to nested dictionary d using keys in order."""
    target = d
    for i in range(len(keys)-1):
        target = target[keys[i]]
    target[keys[-1]] = val

def dictDiffs(*dicts):
    """
    Returns a list of lists about the differences between the input
    dictionaries. Assumes that all input dictionaries have the same
    keys as the first dictionary in the list. Each list is of the form
    [["key1", "key2"...], val1, val2...] for the differences. Works
    recursively for dictionaries inside dictionaries.
    """
    diffLists = []
    first = dicts[0]
    rest = dicts[1:]
    for key in first:
        if type(first[key]) == dict:
            innerDicts = []
            for d in dicts:
                innerDicts.append(d[key])
            nextLists = dictDiffs(*innerDicts)
            nextLists[0] = [key] + nextLists[0]
            diffLists.extend(nextLists)
        else:
            for r in rest:
                if first[key] != r[key]:
                    diff = [[key]]
                    for d in dicts:
                        diff.append(d[key])
                    diffLists.append(diff)
                    break
    return diffLists

stat = "{0:^{1}}   "
def printDiffs(diffLists, *titles):
    """
    Given diffLists from dictDiffs and the title of each dict, neatly prints
    the results from the diff.
    """
    longest = [0]
    for title in titles:
        longest.append(len(title))
    for diff in diffLists:
        for i in range(len(diff)):
            longest[i] = max(longest[i], len(str(diff[i])))
    line = stat.format("", longest[0])
    for title, size in zip(titles, longest[1:]):
        line += stat.format(title, size)
    print line
    for diff in diffLists:
        line = stat.format(diff[0], longest[0])
        i = 1
        for val, size in zip(diff[1:], longest[1:]):
            line += stat.format(val, size)
        print line

def print_table(data):
    """
    Given a list of lists, print data as a nice table.
    Each list in the list of lists should be one column of the table.
    """
    if len(data[0]) == 0:
        return
    widths = [] 
    for coll in data:
        widths.append(max(len(str(word)) for word in coll) + 2)
    for i in range(len(data[0])):
        line = ""
        for j in range(len(data)):
            line += str(data[j][i]).center(widths[j])
        print line

def table_diff(*tables):
    """
    Given input tables, return list of diff tables or list of Nones if no diffs
    """
    output_tables = []
    tab = tables[0]
    n_cols = len(tab)
    n_rows = len(tab[0])
    headers = []
    for column in tab:
        headers.append([column[0]])
    for tab in tables:
        output_tables.append(deepcopy(headers))
    rows_with_diffs = []
    for row in range(n_rows):
        if row == 0:
            continue
        for col in range(n_cols):
            vals = set()
            for tab in tables:
                vals.add(tab[col][row])
            if len(vals) > 1:
                rows_with_diffs.append(row)
                break
    if len(rows_with_diffs) == 0:
        return [None] * len(tables)
    for i, tab in enumerate(tables):
        for row in rows_with_diffs:
            for col in range(n_cols):
                output_tables[i][col].append(tab[col][row])
    identical_cols = []
    for col in range(n_cols):
        if col == 0:
            continue
        check = []
        for tab in output_tables:
            check.append(tab[col])
        all_same = True
        for ch in check:
            if ch != check[0]:
                all_same = False
                break
        if all_same:
            identical_cols.append(col)
    identical_cols.reverse()
    for col in identical_cols:
        for tab in output_tables:
            tab.pop(col)
    return output_tables

