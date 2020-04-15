"""
Module for interacting with edm from python.

Should be expanded to utils for autogenerating screens.
"""
import os
import subprocess
import blutil.config as config

def edm_open(filename, **macros):
    """Open edm file filename with macros."""
    args = edm_args(filename, **macros)
    subprocess.Popen(args)

def edm_open_from(filename, dir, **macros):
    """Open edm file filename from working directory dir with macros."""
    args = edm_args(filename, **macros)
    with open(os.devnull, "w") as null:
        subprocess.Popen(args, cwd=dir, stdout=null, stderr=subprocess.STDOUT)

def edm_args(filename, **macros):
    """Given macros, return args list for subprocess.Popen"""
    args = ["edm", "-x", "-eolc"]
    if macros:
        args.append("-m")
        mac = ""
        for key, value in macros.items():
            mac += "{0}={1},".format(key, value)
        mac = mac[:-1]
        args.append(mac)
    args.append(filename)
    return args 

def edm_hutch_open(filename, **macros):
    """Opens edm file from hutch's working edm directory with macros."""
    edm_open_from(filename, config.EPICS_HUTCH_SCREENS, **macros)

