from os.path import expanduser,join
import pprint
from textwrap import fill
from functools import partial
from blutil import estr, guessBeamline



standardfields = ['desc','steps']

class Procedure(object):
  def __init__(self,procedure_object,status_dir=None, home_session=None,width=70,indent = ' | '):
    if home_session == None:
      home_session = guessBeamline() + "python"
    self._obj = procedure_object
    self._desc = self._obj['desc']
    self._steps= self._obj['steps']
    self._width=width
    self._indent=indent
    for key in self._obj.keys():
      if not (key in standardfields):
	self.__dict__['_'+key] = self._obj[key]
	self.__dict__['_get_'+key] = partial(self._printthis,self.__dict__['_'+key])
	self.__dict__[key] = property(self.__dict__['_get_'+key])

    self.name = self._obj['name']
    if status_dir == None:
      status_dir = expanduser("~")
    statusfilename = home_session+'_procedures_status.txt'
    self._status_file = join(status_dir,statusfilename)

  #if os.path.exists(home+'/.i' + guessBeamline() + 'yrc'):
    #datuser = _rdConfigurationRaw(home+'/.i' + guessBeamline() + 'yrc')
    #dat = tools.dictMerge(dat,datuser)
  

  def start(self):
    self.step = 0
    print self._format(step=self.step,desc=False)



  def next(self):
    if self.step==None:
      self.step=-1
      print "Starting the procedure..."
    self.step+=1
    if self.step>len(self)-1:
      print "Procedure is done, congratulations!"
      self.step = None
    else:
      print self._format(step=self.step,desc=None)

  def __len__(self):
    return len(self._steps)

  def _format(self,step=None,desc=True):
    sl = []
    sl.append(estr(self.name +' Procedure'))
    if desc and self._obj['desc']:
      sl.append(fill(self._desc,width=self._width))
    tdasteps = []
    for stepNo,tstep in enumerate(self._steps):
      tdasteps.append(fill(tstep,width=self._width,
	initial_indent='('+str(stepNo+1)+') ',
	subsequent_indent=' '*4))
    if not step==None:
      dasteps = []
      if step>0:
	dasteps.append(tdasteps[step-1])
      dasteps.append(estr(tdasteps[step]))
      if len(tdasteps)>step+1:
	dasteps.append(tdasteps[step+1])
    else:
      dasteps = tdasteps
	
    sl.extend(dasteps)

    op = ('\n\n').join(sl)
    op = '\n'+op
    return op

  def __str__(self):
    return self._format(step=self.step)
  def __repr__(self):
    return self.__str__()
 

  def _printthis(self,text):
    print fill(text,width=self._width)
    return ''

  def _set_stepNo(self,step):
    try:
      d = loadVar(self._status_file)
    except:
      d = dict()
    d[self.name] = step
    saveVar(self._status_file,d)

  def _get_stepNo(self):
    try: 
      step = loadVar(self._status_file)[self.name]
    except:
      step = None
    return step
  step = property(_get_stepNo,_set_stepNo)


def saveVar(fina,var):
  f=open(fina,'w')
  f.write(pprint.pformat(var))
  f.close()
  
def loadVar(fina):
  f=open(fina)
  var = eval(f.read())
  f.close()
  return var



