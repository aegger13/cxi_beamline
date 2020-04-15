import time
from psp import Pv 
from pswww import pypsElog

class Autopost(object):
    """
    ELOG autopost application.  
    Requires pvNotepad setup to host PVS. 
    e.g.,
    ioc-cxi-elog-post.cfg in ioc/cxi/pvNotepad
    """
    _kws = ['tag1','tag2','tag3','file','file2','file3','runnum']
    _pvs = {
            'TITLE':    {'pv': 'CXI:ELOG:TITLE',   'type': str,
                         'default': '',
                         'desc': 'Elog message title'},
            'TXTFILE':  {'pv': 'CXI:ELOG:TXTFILE',   'type': str,
                         'default': '',
                         'desc': 'Elog message text file'},
            'tag1':     {'pv': 'CXI:ELOG:TAG1',   'type': str,
                         'default': '',
                         'desc': 'Tag1'},
            'tag2':     {'pv': 'CXI:ELOG:TAG2',   'type': str,
                         'default': '',
                         'desc': 'Tag2'},
            'tag3':     {'pv': 'CXI:ELOG:TAG3',   'type': str,
                         'default': '',
                         'desc': 'Tag3'},
            'file':     {'pv': 'CXI:ELOG:FILE',   'type': str,
                         'default': '',
                         'desc': 'Attachment file1'},
            'file2':    {'pv': 'CXI:ELOG:FILE2',   'type': str,
                         'default': '',
                         'desc': 'Attachment file2'},
            'file3':    {'pv': 'CXI:ELOG:FILE3',   'type': str,
                         'default': '',
                         'desc': 'Attachment file3'},
            'EXP':      {'pv': 'CXI:ELOG:EXP',   'type': str,
                         'default': 'current',
                         'desc': 'Elog experiment'},
            'runnum':   {'pv': 'CXI:ELOG:RUN',    'type': int,
                         'default': 0,
                         'desc': 'Run number'},
            'POST':     {'pv': 'CXI:ELOG:POST',    'type': int,
                         'default': 0,
                         'desc': 'Post Message'},
           }

    def __init__(self):
        self.howto()
        #self.elog = pypsElog.pypsElog()
        for pv,item in self._pvs.items():
            print 'Adding ',pv, item
            item['Pv'] = Pv.Pv(item['pv'])
            setattr(self, pv, item['default'])
            Pv.put(item['pv']+'.DESC', item['desc'])

        self.EXP = 'current'
        self.run()

    def howto(self):
        """
        Instructions
        """
        print('-'*72)
        print('Set Title:         caput CXI:ELOG:TITLE "test title"')
        print('Post message:      caput CXI:ELOG:POST 1')
        print('Optional:')
        print('-Add text file:    caput CXI:ELOG:TXTFILE "/tmp/testtext.txt')
        for kw in self._kws:
            pvinfo = self._pvs.get(kw,{})
            print('-{:17} caput {:} "XXX"'.format(pvinfo.get('desc','')+':',pvinfo.get('pv')))
        print('-'*72)

    def run(self):
        """Auto run elog poster
            elog.submit(self, text='TEXT TO DELETE', 
                              tag=None, tag2=None, tag3=None, 
                              file=None, file_descr='description not known', 
                              file2=None, file_descr2='description not known', 
                              file3=None, file_descr3='description not known', runnum=None)
        """
        while True:
            try:
                time.sleep(1)
                if self.POST:
                    message = self.TITLE
                    runnum = self.RUN
                    exp = self.EXP
                    if self.RUN > 0:
                        runnum = self.RUN
                    else:
                        runnum = None
                    msg = 'posting {:} to {:} experiment'.format(message, exp)
                    post_kwargs = {}
                    for kw in self._kws:
                        kwval = getattr(self, kw)
                        if kwval:
                            post_kwargs[kw] = kwval
                    print(msg, post_kwargs)
                    pypsElog.submit(message, runnum=runnum, **post_kwargs)
                    #self.elog.submit(message, runnum=runnum)
                    for pv, item in self._pvs.items():
                        print(pv, getattr(self, pv), Pv.get(item['pv']+'.DESC'))
                        setattr(self, pv, item['default'])
                        Pv.put(item['pv']+'.DESC', item['desc'])

            except KeyboardInterrupt:
                print('Exiting autopost...')
                break

    def __getattr__(self, attr):
        if attr in self._pvs:
            return self._pvs[attr]['Pv'].get()

    def __setattr__(self, attr, value):
        if attr in self._pvs:
            return self._pvs[attr]['Pv'].put(value)
        else:
            self.__dict__[attr] = value

    def __dir__(self):
        all_attrs = set(self._pvs.keys() +
                        self.__dict__.keys() + dir(Experiment))

        return list(sorted(all_attrs))
 
if __name__ == "__main__":
    autopost = Autopost()
 
