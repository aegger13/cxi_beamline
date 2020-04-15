from blutil import config
from blutil import printnow
from importlib import import_module

def imp_module(module_name, module_path):
    """Import a module from a given path.
    """
    import traceback
    import imp
    import sys
    try:
        if not isinstance(module_path,list):
            module_path = [module_path]
        file,filename,desc = imp.find_module(module_name, module_path)
        globals()[module_name] = imp.load_module(module_name, file, filename, desc)
        return
    except Exception as err:
        print 'import_module error', err
        print 'ERROR loading {:} from {:}'.format(module_name, module_path)
        traceback.print_exc()
        return

    sys.exit()

def get_class(module_name, module_path, class_name, reload=False):
    """Get a class from module_path/module_name file.
    """
    if reload or module_name not in globals():
        imp_module(module_name, module_path)
    
    new_class =  getattr(globals()[module_name],class_name)

    return new_class

def loadx(experiment=None, path=None, module=None, name='Experiment'):
    """Load experiment class object as x into __main__.
       Will update x from saved file.
    """
    import os
    import __main__
    if experiment is None:
        experiment = config.Elog.experiment['name']
    if not path:
        path = os.path.dirname(__file__)
    if not module:
        module = experiment
    try:
        print 'Importing {:} from {:}/{:} and setting as x...'.format(name,path,module)
        exp_obj = get_class(module,path,name, reload=True)
        setattr(__main__,'x', exp_obj())
    except:
        import traceback
        traceback.print_exc()
        print 'Error Importing {:} from {:}/{:}'.format(name,path,module)
        return

def load_exp(experiment=None):
  if experiment is None:
    experiment = config.Elog.experiment['name']
  currExp = import_module('experiments.%s'%experiment)
  exp_obj = currExp.Experiment()
  return exp_obj

