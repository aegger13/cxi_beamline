from blutil import config, printnow
from blutil.organize import SimpleContainer
from experiments import load_exp

printnow("Loading active experiment {0}...".format(config.expname))
try:
    exp_obj = load_exp(config.expname)
    print "...done!"
except Exception, e:
    print e
    print "Failed!"
    exp_obj = SimpleContainer()

