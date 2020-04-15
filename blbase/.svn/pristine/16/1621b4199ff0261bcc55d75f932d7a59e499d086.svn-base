import logging

import pyca
import psp.Pv as Pv


log = logging.getLogger(__name__)

class DeviceMeta(type):
    """
    Special class instantiation instructions to create EPICS properties
    """
    def __init__(cls, name, bases, body):
        super(DeviceMeta, cls).__init__(name, bases, body)
        cls._create_properties()

class Device(object):
    """
    A generic object to interface with a set of EPICS Records.
    """
    # Magic call to incorporate metaclass instructions
    __metaclass__ = DeviceMeta
    _records = {}

    def __init__(self, prefix='', delim=':'):
        self.prefix = prefix
        self.delim  = delim

        self._pvs = {alias : self._assemble(record)
                     for alias, record in self._records.items()} 

    @classmethod
    def _create_properties(cls):
        """
        Private method to construct epics pv properties at class creation
        """
        records = cls._records
        for alias, record in cls._records.items():
            if not alias:
                alias = record.replace(":", "_")
#            pv_property = property(lambda self:
#                                       cls.get(self, record),
#                                   lambda self, value:
#                                       cls.put(self, record, value))
            pv_property = property(lambda self,record=record:
                                       cls.get(self, record),
                                   lambda self,value,record=record:
                                       cls.put(self, record, value))
            setattr(cls, alias, pv_property)

    def get(self, attr, use_prefix=True, delim=None, as_string=False):
        """
        Get an EPICS PV value

        The PV can either be referred to by the alias given, or the EPICS PV
        designation. In the latter case, the PV can be assembled automatically
        based on the prefix and delim attributes, or the absolute PV name can 
        be given. 
        
        .. code-block:: python
            
            d = Device(prefix='CXI:DG2:MMS:01',delim='.')
            
            # These are all equivalent
            d.position
            #   and 
            d.get('RBV')
            #   and
            d.get('position')
            #   and
            d.get('CXI:DG2:MMS:01.RBV',use_prefix=False)

        :param attr: The name of the PV
        :type  attr: str
        
        :param use_prefix: Append the PV name to the end of the device prefix
        :type  use_prefix: bool

        :param delim: The seperator to use between the prefix and the PV. By
                      default, this will be the class :attr:`.delim` attribute
        :type  delim: str

        :param as_string: The choice to return the EPICS PV value as a string
        :type  as_string: True
        """
        pv = self.PV(attr, use_prefix=use_prefix, delim=delim)
        
        if not pv:
            return None

        if as_string:
            return str(pv.value)
        
        return pv.value


    def put(self, attr, value, use_prefix=True, delim=None):
        """
        Put a value to an EPICS PV
        
        The PV can either be referred to by the alias given, or the EPICS PV
        designation. In the latter case, the PV can be assembled automatically
        based on the prefix and delim attributes, or the absolute PV name can 
        be given. 
        
        .. code-block:: python
            
            d = Device(prefix='CXI:DG2:MMS:01',delim='.')
            d.add_pv('VAL',alias='setpoint')
            
            #These are all equivalent
            d.setpoint = 4.0
            #   and 
            d.put('VAL',4.0)
            #   and
            d.put('setpoint',4.0)
            #   and
            d.put('CXI:DG2:MMS:01.VAL',4.0,use_prefix=False)
        
        :param attr: The name of the PV
        :type  attr: str
        
        :param value: The value to be sent to the PV
        :type  value: float,int,str,waveform

        :param use_prefix: Append the PV name to the end of the device prefix
        :type  use_prefix: bool

        :param delim: The seperator to use between the prefix and the PV. By
                      default, this will be the class :attr:`.delim` attribute
        :type  delim: str

        """
        pv = self.PV(attr, use_prefix=use_prefix, delim=delim)

        if not pv:
            return None

        pv.put(value)
    
    def PV(self, pv, use_prefix=True, delim=None):
        """
        Return a PV object
        
        The PV can either be referred to by the alias given, or the EPICS PV
        designation. In the latter case, the PV can be assembled automatically
        based on the prefix and delim attributes, or the absolute PV name can 
        be given. 
        
        :param pv: The name of the PV
        :type  pv: str

        :param use_prefix: Append the PV name to the end of the device
                           :attr:`prefix'
        :type  use_prefix: bool

        :param delim: The seperator to use between the prefix and the PV. By
                      default, this will be the class :attr:`.delim` attribute
        :type  delim: str
        """
        if pv in self._pvs.keys():
            pv = self._pvs[pv]
        
        elif use_prefix:
            pv = self._assemble(pv, delim=delim)

        return self._pv(pv)


    def _pv(self, pv):
        """
        Load a PV object from the cache
        """ 
        obj = Pv.add_pv_to_cache(pv)

        if not obj.ismonitored:
            try:
                obj.monitor()
                obj.get() #Will be unneccessary in new release of PSP
            except pyca.pyexc as e:
                log.exception('Unable to get EPICS PV {:}'.format(pv))
                return None

        return obj


    def _assemble(self, pv, delim=None):
        """
        Assemble a PV name
        """
        if not delim:
            delim = self.delim

        return self.prefix + delim + pv
