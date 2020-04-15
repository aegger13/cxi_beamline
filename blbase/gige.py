import os
import psp.Pv as Pv
import subprocess
from time import sleep

class GigeCam(object):
    def __init__(self, pvname, path=None, filename=None, fileformat=None, filenum=None, plugin='JPEG1'):
        self.pvname = pvname
        self.__plugin = plugin
        self._next_filenum = -1
        self.__lstr_pv_limit = 256
        self.__enable          = self.__create_pv('EnableCallbacks', is_str=True)
        self.__array_port      = self.__create_pv('NDArrayPort')
        self.__array_port_rbv  = self.__create_pv('NDArrayPort_RBV')
        self.__filepath_rbv    = self.__create_pv('FilePath_RBV')
        self.__filepath        = self.__create_pv('FilePath')
        self.__filepath_stat   = self.__create_pv('FilePathExists_RBV', is_str=True)
        self.__filename_rbv    = self.__create_pv('FileName_RBV')
        self.__filename        = self.__create_pv('FileName')
        self.__fileformat_rbv  = self.__create_pv('FileTemplate_RBV')
        self.__fileformat      = self.__create_pv('FileTemplate')
        self.__filename_full   = self.__create_pv('FullFileName_RBV')
        self.__filenum         = self.__create_pv('FileNumber')
        self.__auto_save       = self.__create_pv('AutoSave', is_str=True)
        self.__auto_incr       = self.__create_pv('AutoIncrement', is_str=True)
        self.__capture_mode    = self.__create_pv('FileWriteMode', is_str=True)
        self.__capture_num_rbv = self.__create_pv('NumCapture_RBV')
        self.__capture_num     = self.__create_pv('NumCapture')
        self.__capture         = self.__create_pv('Capture', is_str=True)
        self.__capture_rbv     = self.__create_pv('Capture_RBV', is_str=True, monitor=True)
        self.__write_rbv       = self.__create_pv('WriteFile_RBV', is_str=True, monitor=True)
        self.__write_stat      = self.__create_pv('WriteStatus', is_str=True, monitor=True)
        self.__model_rbv       = self.__create_pv('Model_RBV', is_plugin_pv=False)
        self.__image_mode      = self.__create_pv('ImageMode', is_str=True, is_plugin_pv=False)
        self.__image_mode_rbv  = self.__create_pv('ImageMode_RBV', is_str=True, is_plugin_pv=False)
        self.__trig_mode       = self.__create_pv('TriggerMode', is_str=True, is_plugin_pv=False)
        self.__trig_mode_rbv   = self.__create_pv('TriggerMode_RBV', is_str=True, is_plugin_pv=False)
        self.__expose_time     = self.__create_pv('AcquireTime', is_plugin_pv=False)
        self.__expose_time_rbv = self.__create_pv('AcquireTime_RBV', is_plugin_pv=False)
        self.__exp_period      = self.__create_pv('AcquirePeriod', is_plugin_pv=False)
        self.__exp_period_rbv  = self.__create_pv('AcquirePeriod_RBV', is_plugin_pv=False)
        self.__gain            = self.__create_pv('Gain', is_plugin_pv=False)
        self.__gain_rbv        = self.__create_pv('Gain_RBV', is_plugin_pv=False)
        self.__img_num         = self.__create_pv('NumImages', is_plugin_pv=False)
        self.__img_num_rbv     = self.__create_pv('NumImages_RBV', is_plugin_pv=False)
        self.__rate_rbv        = self.__create_pv('ArrayRate_RBV', is_plugin_pv=False)
        self.__count_rbv       = self.__create_pv('ArrayCounter_RBV', is_plugin_pv=False)
        self.__det_state_rbv   = self.__create_pv('DetectorState_RBV', is_plugin_pv=False, is_str=True)
        self.__res_x_rbv       = self.__create_pv('ArraySizeX_RBV', is_plugin_pv=False)
        self.__res_y_rbv       = self.__create_pv('ArraySizeY_RBV', is_plugin_pv=False)
        self.__roi_min_x_rbv   = self.__create_pv('MinX_RBV', is_plugin_pv=False)
        self.__roi_min_y_rbv   = self.__create_pv('MinY_RBV', is_plugin_pv=False)
        self.__roi_size_x_rbv  = self.__create_pv('SizeX_RBV', is_plugin_pv=False)
        self.__roi_size_y_rbv  = self.__create_pv('SizeY_RBV', is_plugin_pv=False)
        self.__roi_min_x       = self.__create_pv('MinX', is_plugin_pv=False)
        self.__roi_min_y       = self.__create_pv('MinY', is_plugin_pv=False)
        self.__roi_size_x      = self.__create_pv('SizeX', is_plugin_pv=False)
        self.__roi_size_y      = self.__create_pv('SizeY', is_plugin_pv=False)
        # initialize PVs with passed parameters
        if path is not None:
            self.put_str(self.__filepath, path)
        if filename is not None:
            self.put_str(self.__filename, filename)
        if fileformat is not None:
            self.put_str(self.__fileformat, fileformat)
        if filenum is not None:
            self.put(self.__filenum, filenum)
        

    def __create_pv(self, name, is_str=False, monitor=False, is_plugin_pv=True):
        if is_plugin_pv:
            pv = Pv.Pv('%s:%s:%s'%(self.pvname, self.__plugin, name),
                       initialize=True, monitor=monitor)
        else:
            pv = Pv.Pv('%s:%s'%(self.pvname, name),
                       initialize=True, monitor=monitor)
        if is_str:
            pv.set_string_enum(True)
        return pv

    def put(self, param, val):
        param.put(val)

    def put_str(self, param, val):
        char_arr = [0] * self.__lstr_pv_limit
        for i, char in enumerate(val):
            if i >= self.__lstr_pv_limit:
                raise ValueError('string exceeds max length of %d characters' % self.__lstr_pv_limit)
            char_arr[i] = ord(char)
        param.put(tuple(char_arr))

    def get(self, param):
        return param.get()

    def get_str(self, param):
        byte_array = self.get(param)
        char_array = [ chr(char_val) for char_val in byte_array if char_val != 0 ]
        return ''.join(char_array)

    def _prep_gige(self, filepath=None, filename=None, fileformat=None, filenum=None):
        if filepath is not None:
            self.filepath = filepath
        if filename is not None:
            self.filename = filename
        if fileformat is not None:
            self.fileformat = fileformat
        if filenum is not None:
            self.filenum  = filenum

    def setTrigger(self, evr):
        self.trigger = evr

    @property
    def plugin(self):
        return self.__plugin

    @property
    def enable(self):
        return self.get(self.__enable)

    @enable.setter
    def enable(self, setting):
        self.put(self.__enable, setting)

    @property
    def port(self):
        return self.get(self.__array_port_rbv)

    @port.setter
    def port(self, port):
        self.put(self.__array_port, port)

    @property
    def filepath(self):
        return self.get_str(self.__filepath_rbv)

    @filepath.setter
    def filepath(self, path):
        self.put_str(self.__filepath, path)

    @property
    def filepath_exists(self):
        return self.get_str(self.__filepath_stat)

    @property
    def filename(self):
        return self.get_str(self.__filename_rbv)

    @filename.setter
    def filename(self, name):
        return self.put_str(self.__filename, name)

    @property
    def fileformat(self):
        return self.get_str(self.__fileformat_rbv)

    @fileformat.setter
    def fileformat(self, format):
        return self.put_str(self.__fileformat, format)

    @property
    def file(self):
        return self.get_str(self.__filename_full)

    @property
    def filenum(self):
        return self.get(self.__filenum)

    @filenum.setter
    def filenum(self, num):
        self.put(self.__filenum, num)

    @property
    def auto_save(self):
        return self.get(self.__auto_save)

    @auto_save.setter
    def auto_save(self, setting):
        self.put(self.__auto_save, setting)

    @property
    def auto_increment(self):
        return self.get(self.__auto_incr)

    @auto_increment.setter
    def auto_increment(self, setting):
        self.put(self.__auto_incr, setting)

    @property
    def capture_num(self):
        return self.get(self.__capture_num_rbv)

    @capture_num.setter
    def capture_num(self, num):
        self.put(self.__capture_num, num)

    @property
    def capture_mode(self):
        return self.get(self.__capture_mode)

    @capture_mode.setter
    def capture_mode(self, setting):
        self.put(self.__capture_mode, setting)

    def capture(self):
        self._next_filenum = self.filenum + 1
        self.put(self.__capture, 'Capture')

    def wait(self):
        while self.capture_state != 'Done' or self.write_state != 'Done' or self._next_filenum > self.filenum:
            sleep(0.01)

    @property
    def capture_state(self):
        return self.get(self.__capture_rbv)

    @property
    def write_status(self):
        return self.get(self.__write_stat)

    @property
    def write_state(self):
        return self.get(self.__write_rbv)

    @property
    def model(self):
        return self.get(self.__model_rbv)

    @property
    def image_mode(self):
        return self.get(self.__image_mode_rbv)

    @image_mode.setter
    def image_mode(self, img_mode):
        self.put(self.__image_mode, img_mode)

    @property
    def trigger_mode(self):
        return self.get(self.__trig_mode_rbv)

    @trigger_mode.setter
    def trigger_mode(self, trig_mode):
        self.put(self.__trig_mode, trig_mode)

    @property
    def gain(self):
        return self.get(self.__gain_rbv)

    @gain.setter
    def gain(self, gain):
        self.put(self.__gain, gain)

    @property
    def image_num(self):
        return self.get(self.__img_num_rbv)

    @image_num.setter
    def image_num(self, num):
        self.put(self.__img_num, num)

    @property
    def exposure_time(self):
        return self.get(self.__expose_time_rbv)

    @exposure_time.setter
    def exposure_time(self, expose_time):
        self.put(self.__expose_time, expose_time)

    @property
    def exposure_period(self):
        return self.get(self.__exp_period_rbv)

    @exposure_period.setter
    def exposure_period(self, exp_period):
        self.put(self.__exp_period, exp_period)

    @property
    def rate(self):
        return self.get(self.__rate_rbv)

    @property
    def count(self):
        return self.get(self.__count_rbv)

    @property
    def state(self):
        return self.get(self.__det_state_rbv)

    @property
    def res_x(self):
        return self.get(self.__res_x_rbv)

    @property
    def res_y(self):
        return self.get(self.__res_y_rbv)

    @property
    def resolution(self):
        return self.res_x, self.res_y

    @property
    def roi_min_x(self):
        return self.get(self.__roi_min_x_rbv)

    @property
    def roi_size_x(self):
        return self.get(self.__roi_size_x_rbv)

    @property
    def roi_min_y(self):
        return self.get(self.__roi_min_y_rbv)

    @property
    def roi_size_y(self):
        return self.get(self.__roi_size_y_rbv)

    @roi_min_x.setter
    def roi_min_x(self, val):
        self.put(self.__roi_min_x, val)

    @roi_min_y.setter
    def roi_min_y(self, val):
        self.put(self.__roi_min_y, val)

    @roi_size_x.setter
    def roi_size_x(self, val):
        self.put(self.__roi_size_x, val)

    @roi_size_y.setter
    def roi_size_y(self, val):
        self.put(self.__roi_size_y, val)

    @property
    def roi(self):
        return (self.roi_min_x, self.roi_size_x), (self.roi_min_y, self.roi_size_y)

    @roi.setter
    def roi(self, roi_tuple):
        (self.roi_min_x, self.roi_size_x), (self.roi_min_y, self.roi_size_y) = roi_tuple

    def plugin_screen(self):
        """ Opens gigE plugin screen"""
        expdir = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile('%s/gige-plugin-screen'%expdir):
          os.system('%s/gige-plugin-screen %s'%(expdir, self.pvname))
        else:
          os.system('gige-plugin-screen %s'%self.pvname)

    def expert_screen(self):
        """ Opens gigE expert screen"""
        expdir = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile('%s/gige-plugin-screen'%expdir):
          os.system('%s/gige-plugin-screen -e %s'%(expdir, self.pvname))
        else:
          os.system('gige-plugin-screen -e %s'%self.pvname)

    def status(self):
        """ return info for the gige camera"""
        s  = "gigE Camera\n\tpv: %s\n" % self.pvname
        s += "\tmodel: %s\n" % self.model
        s += "\tresolution: %dx%d\n" % (self.res_x, self.res_y)
        s += "\timage mode: %s\n" % self.image_mode
        if self.image_mode == 'Multiple':
            s += "\timage num: %d\n" % self.image_num
        s += "\ttrigger mode: %s\n" % self.trigger_mode
        s += "\trate: %.2f Hz\n" % self.rate
        s += "\tgain: %d\n" % self.gain
        s += "\texposure time: %.3f\n" % self.exposure_time
        if self.trigger_mode == 'Fixed Rate':
            s += "\texposure period: %.3f\n" % self.exposure_period
        s += "\tplugin: %s\n" % self.plugin
        s += "\tplugin mode: %s\n" % self.capture_mode
        if self.capture_mode == 'Capture':
            s += "\tcapture number: %s\n" % self.capture_num
        s += "\tfile path: %s\n" % self.filepath
        s += "\tfile name: %s\n" % self.filename
        s += "\tfile num: %d\n" % self.filenum
        s += "\tfile format: %s\n" % self.fileformat
        s += "\tfile autosave: %s\n" % self.auto_save
        s += "\tlast file written: %s\n" % self.file
        return s

    def __repr__(self):
        return self.status()        
