from blutil import config
from blutil import printnow
from importlib import import_module

def load_exp(experiment=None):
  if experiment is None:
    experiment = config.Elog.experiment['name']
  currExp = import_module('experiments.%s'%experiment)
  exp_obj = currExp.Experiment()
  return exp_obj

