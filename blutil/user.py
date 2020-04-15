"""
Utilites for incorporating user experiment files.

load_exp is a catch-all macro for loading the most relevant experiment file.
The heirarchy is user files > experiment files > backup_func

User files should be checked in to the hutch/experiments directory after the
experiment.
"""
import os
import sys
import importlib
import traceback
import re

def load_exp(user_file=None, user_obj=None, experiment=None, exp_obj=None,
             backup_func=None, elog=None, verbose=True):
    """
    Return experiment module or object.

    Sources user_file first, then tries file in $hutch/experiments, and last
    tries to run backup_func.

    Parameters
    ----------
    user_file : string, optional
        Full filepath to the user's code to be imported. We will modify this
        as user_file.format(experiment) if it doesn't throw an exception.

    user_obj : string or list or strings, optional
        If provided, we'll return objects from user_file. If not provided,
        we'll return the full module object. We will modify this as
        user_obj.format(experiment) if it doesn't throw an exception.

    experiment : string, optional
        Name of experiment module to be imported. If not provided and elog is
        available, we'll set this using the elog.

    exp_obj : string or list of strings, optional
        If provided, we'll return objects from the experiment file. If not
        provided, we'll return the full module object. We will modify this as
        exp_obj.format(experiment) if it doesn't throw an exception.

    objname : string, optional
        Name of object to return from the experiment module. If not supplied,
        we'll just return the module instead of an object.

    backup_func : function, optional
        If this exists and experiment does not load, we'll run this function
        to get a default experiment object. Expects no arguments.

    elog : pswww.pypsElog.pypsElog, optional
        If provided and experiment is None, use the Elog to get the experiment
        name and use it as the experiment parameter.

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    exp : object, list of objects, or None
        object representing experiment-specific code
    """
    # Load experiment name if not provided
    if experiment is None and elog is not None:
        try:
            experiment = elog.experiment["name"]
        except:
            if verbose:
                warn("Issues loading experiment name from Elog!")

    # First, let's try to load the user file.
    if user_file is not None:
        exp = user_module_obj(user_file, user_obj=user_obj,
                              experiment=experiment, verbose=verbose)
        if exp is not None:
            print "Using user file at {}".format(sys.modules[exp.__module__].__file__)
            return exp

    # Second, try the experiments folder.
    if experiment is not None:
        exp = exp_module_obj(experiment, exp_obj=exp_obj, verbose=verbose)
        if exp is not None:
            print "Using experiment file {}".format(experiment)
            return exp

    # Last, run our backup if available
    if backup_func is not None:
        print "Using default experiment"
        return backup_func()

def exp_module(experiment, verbose=True):
    """
    Import the experiment file from $hutch/experiments

    Parameters
    ----------
    experiment : string
        experiment name

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    module : module or None
        the relevant experiments folder module object
    """
    try:
        return importlib.import_module("experiments." + experiment)
    except:
        diagnose_import_error(experiment, verbose=verbose)

def exp_module_obj(experiment, exp_obj=None, verbose=True):
    """
    Import the experiment file and extract objects.

    Parameters
    ----------
    experiment : string
        experiment name

    exp_obj : string or list of strings, optional
        Objects to return from experiment module. We'll replace them with
        exp_obj.format(experiment) if applicable.
        
    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    exp : object, list of objects, or None
        object representing experiment-specific code
    """
    module = exp_module(experiment, verbose=verbose)
    if exp_obj is None:
        return module
    if module is not None:
        exp_obj = format_all(exp_obj, experiment)
        exp = module_extract(module, exp_obj, experiment)
        if exp is not None:
            return exp

def user_module(filepath, module_paths=[], verbose=True):
    """
    Import the file at filepath without modifying sys.path.

    If something goes wrong, identify where the error is and expose the
    traceback.

    A few notes:
    - Any changes the user makes to sys.path will be reverted.
    - We can't allow name conflicts between user-supplied modules and modules
      that hutch python loads: hutch python modules will take precedence.

    Parameters
    ----------
    filepath : string
        full path to the user's file

    module_paths : list of strings, optional
        full paths to module dependencies of user module

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    module : module or None
        the module defined by the python code at filepath
    """
    all_paths = [os.path.dirname(filepath)] + module_paths
    with PathContext(*all_paths):
        module_name = filepath.split(".")[0].split("/")[-1]
        try:
            return importlib.import_module(module_name)
        except:
            diagnose_import_error(module_name, verbose=verbose)

def user_module_obj(user_file, module_paths=[], user_obj=None, experiment=None,
                    verbose=True):
    """
    Import the user file and extract objects.

    Parameters
    ----------
    user_file : string
        Full file path to user module. We'll replace this with
        user_file.format(experiment) if applicable.

    module_paths : list, optional
        Additional locations of modules that we need to import user_file.

    user_obj : string or list of strings, optional
        Objects to return from experiment module. We'll replace them with
        user_obj.format(experiment) if applicable.

    experiment : string, optional
        Experiment name to use as formatter in string arguments.

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    exp : object, list of objects, or None
        object representing experiment-specific code
    """
    if experiment is not None:
        try:
            user_file = user_file.format(experiment)
        except:
            pass

    if not os.path.exists(user_file):
        if verbose:
            warn("File {} does not exist!".format(user_file))
        return

    module = user_module(user_file, module_paths=module_paths, verbose=verbose)
    if user_obj is None:
        return module
    if module is not None:
        user_obj = format_all(user_obj, experiment)
        exp = module_extract(module, user_obj, user_file)
        if exp is not None:
            return exp

def diagnose_import_error(module_name, verbose=True):
    """
    Determine when an error was raised during the experiment file import.
    It's important to make a distinction between being unable to find the
    module and having errors in the experiment file.

    If the error is in the user's code, print a traceback.

    Parameters
    ----------
    module_name : string
        name of the module we're trying to import

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.
    """
    info = sys.exc_info()
    exc = info[1]
    tb = info[2]
    tb_info = traceback.extract_tb(tb)

    all_filepaths = []
    # Check for exceptions that don't make it into the tb stack.
    # One example is SyntaxError which is raised in the module that imports
    # the offending module, rather than in the module with the error, so the
    # filepath is stored in the exception rather than in the traceback.
    try:
        all_filepaths.append(exc.filename)
    except AttributeError:
        pass
    # Check for normal exceptions
    all_filepaths.extend([tbi[0] for tbi in tb_info])

    expected = module_name.split(".")

    for filepath in all_filepaths:
        actual = re.split("\.|/", filepath)[:-1]
        if actual[-1] == "__init__":
            actual = actual[:-1]
        if expected == actual[-len(expected):]:
            sys.excepthook(*info)
            warn("Error in user code!")
            return
    if verbose:
        warn("Error finding module {}!".format(module_name))

class PathContext(object):
    """
    Context manager to execute a block of python code with a different python
    path. Revert to the normal path once finished.

    Parameters
    ----------
    *paths : strings
        full paths to check, in order, before our normal python paths
    """
    def __init__(self, *paths):
        self.paths = list(paths)

    def __enter__(self):
        self.original_path = sys.path
        sys.path = self.paths + sys.path

    def __exit__(self, err_type, err_value, traceback):
        sys.path = self.original_path

def module_extract(module, name, filename):
    """
    Pull objects out of a module object by name, skipping objects that do not
    exist and displaying a warning message.

    Parameters
    ----------
    module : module
        module to extract objects from

    name : string or list of strings
        name or names to extract from module

    filename : string
        source filename used in the warning message

    verbose : bool, optional
        If False, we'll suppress warning messages about being unable to find
        modules. Tracebacks from user modules will still be printed, as these
        are important.

    Returns
    -------
    objs : user-defined object, list of such objects, or None
        objects extracted from the module
    """
    if isinstance(name, (list, tuple)):
        objs = []
        for n in name:
            obj = module_extract(module, n, filename)
            if obj is not None:
                objs.append(obj)
        return objs
    else:
        try:
            return getattr(module, name)
        except AttributeError:
            warn("No object {0} defined in {1}!".format(name, filename))

def warning(txt):
    """
    Return a warning message in bold, red text.

    Parameters
    ----------
    txt : string
        text to use

    Returns
    -------
    txt : string
        same text, colored red and bolded
    """
    return "\x1b[31m\x1b[1m" + str(txt) + "\x1b[0m"

def warn(txt):
    """
    Print a warning message in bold, red text.

    Parameters
    ----------
    txt : string
        text to use
    """
    print warning(txt)

def format_all(strings, *text):
    """
    Format all strings using arguments *text.
    Will echo back the strings that fail.

    Parameters
    ----------
    strings : string or list of strings
        all strings to format

    *text : valid arguments to String.format

    Returns
    -------
    strings : string or list of strings
        all the inputted strings, formatted if possible
    """
    if isinstance(strings, (list, tuple)):
        formatted = []
        for s in strings:
            formatted.append(format_all(s, *text))
        return formatted
    try:
        strings = strings.format(*text)
    except:
        pass
    return strings
