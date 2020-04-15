import numpy
from psp.Pv import Pv
from blbase.motorutil import tweak2D
from blbase.virtualmotor import VirtualMotor as vmot

class LusiSlitBase(object):
    def __init__(self, name=""):
        self._name = name
        for gap in ["hg", "vg", "ho", "vo"]:
            setattr(self, gap,
                    vmot(name + "_" + gap,
                         getattr(self, "mv_" + gap),
                         getattr(self, "wm_" + gap),
                         set=getattr(self, "set_" + gap)))
        self.hvgap = vmot(name + "_hvgap", self.__call__, self.__call__)

    def __call__(self,hg=None,vg=None):
        if hg is None:
            return self.wm_hg()
        if vg is None:
            vg = hg
        self.mv_hg(hg)
        self.mv_vg(vg)

    def __repr__(self):
        return self.status()

    def status(self):
        self._update()
        out = "slit %s: (hg,vg) = (%+.4f x %+.4f); (ho,vo) = (%+.4f,%+.4f)" % (self._name,\
          self.wm_hg(fast=True),self.wm_vg(fast=True),\
          self.wm_ho(fast=True),self.wm_vo(fast=True) )
        return out

    def tweakpos(self,val=0.1):
        '''Does a 2d tweak of the position of the slit'''
        tweak2D(self.mv_ho,self.mv_vo,mothstep=val,motvstep=val)


class LusiSlit(LusiSlitBase):
    """ Class to control the lusislit
        each slit object is defined by passing the four motor it is connected to.
        (up,down,north,south) plus an optional mnemonic name.
        The 4 motors are combined to provide an offset and gap.
        hg = N-S; ho = (N+S)/2
        vg = U-D; vo = (U+D)/2
        for each [hg,ho,vg,vo] methods are provided to retrieve the value (wm_*)
        move to a given value (mv_*) and set the current position as new value (set_*)
    """
    def __init__(self, u, d, n, s, name=""):
        super(LusiSlit, self).__init__(name=name)
        self.u = u
        self.d = d
        self.n = n
        self.l = n
        self.s = s
        self.r = s
        self.upos = self.dpos = self.spos = self.npos = numpy.nan

    def _update(self):
        self.npos = self.n.wm()
        self.spos = self.s.wm()
        self.upos = self.u.wm()
        self.dpos = self.d.wm()

    def wm_ho(self, fast=False):
        if not fast:
            self._update()
        return (self.npos + self.spos)/2

    def wm_hg(self, fast=False):
        if not fast:
            self._update()
        return self.npos - self.spos

    def wm_vo(self, fast=False):
        if not fast:
            self._update()
        return (self.upos + self.dpos)/2

    def wm_vg(self, fast=False):
        if not fast:
            self._update()
        return self.upos - self.dpos

    def mv_ho(self, offset=0):
        gap = self.wm_hg()
        if (numpy.isnan(gap)):
            print "Problem in getting the current horizontal gap, stopping"
        else:
            self.s.move(offset-gap/2)
            self.n.move(offset+gap/2)

    def set_ho(self, newoffset=0):
        gap = self.wm_hg()
        if (numpy.isnan(gap)):
            print "Problem in getting the current horizontal gap, stopping"
        else:
            self.s.set(newoffset-gap/2)
            self.n.set(newoffset+gap/2)

    def mv_vo(self, offset=0):
        gap = self.wm_vg()
        if (numpy.isnan(gap)):
            print "Problem in getting the current vertical gap, stopping"
        else:
            self.u.move(offset+gap/2)
            self.d.move(offset-gap/2)

    def set_vo(self, newoffset=0):
        gap = self.wm_vg()
        if (numpy.isnan(gap)):
            print "Problem in getting the current vertical gap, stopping"
        else:
            self.d.set(newoffset-gap/2)
            self.u.set(newoffset+gap/2)

    def mv_hg(self, gap=None):
        if (gap is None):
            return
        gap = float(gap)
        offset = self.wm_ho()
        if (numpy.isnan(offset)):
            print "Problem in getting the current horizontal offset position, stopping"
        else:
            self.s.move(offset-gap/2)
            self.n.move(offset+gap/2)

    def set_hg(self, newgap=0):
        newgap = float(newgap)
        offset = self.wm_ho()
        if (numpy.isnan(offset)):
            print "Problem in getting the current horizontal offset position, stopping"
        else:
            self.s.set(offset-newgap/2)
            self.n.set(offset+newgap/2)

    def mv_vg(self, gap=None):
        if (gap is None):
            return
        gap = float(gap)
        offset = self.wm_vo()
        if (numpy.isnan(offset)):
            print "Problem in getting the current vertical offset position, stopping"
        else:
            self.d.move(offset-gap/2)
            self.u.move(offset+gap/2)

    def set_vg(self, newgap=0):
        newgap = float(newgap)
        offset = self.wm_vo()
        if (numpy.isnan(offset)):
            print "Problem in getting the current vertical offset position, stopping"
        else:
            self.d.set(offset-newgap/2)
            self.u.set(offset+newgap/2)

    def wait(self):
        self.d.wait()
        self.u.wait()
        self.s.wait()
        self.n.wait()

    def waith(self):
        self.s.wait()
        self.n.wait()

    def waitv(self):
        self.d.wait()
        self.u.wait()

    def home(self, ask=True, move_motor_back=True, restoreOffset=False):
        self.s.home(ask, move_motor_back, restoreOffset)
        self.n.home(ask, move_motor_back, restoreOffset)
        self.u.home(ask, move_motor_back, restoreOffset)
        self.d.home(ask, move_motor_back, restoreOffset)


class LusiSlitJaws(LusiSlitBase):
    _class_pvs = dict(
        xcenter_get = "ACTUAL_XCENTER",
        xwidth_get = "ACTUAL_XWIDTH",
        ycenter_get = "ACTUAL_YCENTER",
        ywidth_get = "ACTUAL_YWIDTH",
        xcenter_set = "XCEN_REQ",
        xwidth_set = "XWID_REQ",
        ycenter_set = "YCEN_REQ",
        ywidth_set = "YWID_REQ")

    def __init__(self, prefix, name=""):
        super(LusiSlitJaws, self).__init__(name=name)
        self.pvs = {k: Pv(":".join((prefix, self._class_pvs[k])))
                    for k in self._class_pvs}

    def _update(self):
        pass

    def wm_ho(self, **kwargs):
        return self.pvs['xcenter_get'].get()

    def wm_hg(self, **kwargs):
        return self.pvs['xwidth_get'].get()

    def wm_vo(self, **kwargs):
        return self.pvs['ycenter_get'].get()

    def wm_vg(self, **kwargs):
        return self.pvs['ywidth_get'].get()

    def mv_ho(self, pos, **kwargs):
        self.pvs['xcenter_set'].put(pos)

    def mv_hg(self, pos, **kwargs):
        self.pvs['xwidth_set'].put(pos)

    def mv_vo(self, pos, **kwargs):
        self.pvs['ycenter_set'].put(pos)

    def mv_vg(self, pos, **kwargs):
        self.pvs['ywidth_set'].put(pos)

    def set_ho(self, *args, **kwargs):
        raise NotImplementedError()

    def set_hg(self, *args, **kwargs):
        raise NotImplementedError()

    def set_vo(self, *args, **kwargs):
        raise NotImplementedError()

    def set_vg(self, *args, **kwargs):
        raise NotImplementedError()
