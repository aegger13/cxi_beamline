from collections import OrderedDict
import blutil.calc as calc
import numpy as np

class Rowland(object):
    """ Class for the Rowland motor assembly """
    def __init__(self, rChi, rTheta, rX, rDZ, hkl=(4,4,0), elem="Ge", radius=1000):
        """ Define motors and basic geometry """
        self.rChi = rChi
        self.rTheta = rTheta
        self.rX = rX
        self.rDZ = rDZ
        """ geometry """
        self.hkl = hkl
        self.elem = elem
        self.radius = radius
        self.dSpacing = 10**10 * calc.dSpace(self.elem, self.hkl) # ANGSTROMS

    def getPos(self, energy=None, printIt=True):
        """
        Returns a vector of positions at a certain energy for motors in the
        Rowland. Default is the current energy.
        """
        if energy is None:
            energy = self.getE()

        ## Calculate Bragg angle and the geometry.
        angle = calc.asind(12398.52/(energy*2*self.dSpacing))
        X = self.radius*calc.sind(angle)
        DZ = 2*self.radius*calc.cosd(angle)*calc.sind(angle)

        if printIt:
            print "\n \t angle: \t %.3f" % angle
            print " \t X: \t \t %.3f" % X
            print " \t DZ: \t \t %.3f\n" % (DZ)

        pos = [angle, X, DZ]
        return pos

    def getE(self, angle=None):
        """
        Gets the energy at an input angle. Default is the current angle.
        Energy is in eV.
        """ 
        if angle is None:
            angle = self.rTheta.wm()
        energy = 12398.52/calc.sind(angle)/2/self.dSpacing
        return energy

    def moveE(self, energy, debug=False):
        """
        Moves the motors in the Rowland to match a certain energy. Energy
        is in eV.
        """
        pos = self.getPos(energy, printIt=False)
        if debug:
            print 'mv rTheta from ',self.rTheta.wm(), ' to ',pos[0]
            print 'mv rX from ',self.rX.wm(), ' to ',pos[1]
            print 'mv rDZ from ',self.rDZ.wm(), ' to ',pos[2]
        else:
            self.rTheta.mv(pos[0])
            self.rX.mv(pos[1])
            self.rDZ.mv(pos[2])

    def wait(self):
        """ Halts the thread until all of the motors are done moving. """
        self.rTheta.wait()
        self.rX.wait()
        self.rDZ.wait()

    def status(self):
        """ Prints verbose information about the Rowland status. """
        print "Rowland Status:"
        print "Energy: {0} eV".format(self.getE())
        print "rChi:   {0} deg".format(self.rChi.wm())
        print "rTheta: {0} deg".format(self.rTheta.wm())
        print "rX:     {0} mm".format(self.rX.wm())
        print "rDZ:    {0} mm".format(self.rDZ.wm())

class RowlandN(object):
    """
    Class to handle a Rowland motor assembly with multiple crystals.
    """
    def __init__(self, names, rChi, rTheta, rX, dy, rZ, rDZ,
                 hkl=(4,4,0), elem='Ge', radius=1000):
        """
        Parameters
        ----------
        names : list of strings
            the name assigned to each of the crystals, in order
        rChi : list of Motors
            Motor objects associated with rChi of each crystal, in order
        rTheta : list of Motors
            Motor objects associated with rTheta of each crystal, in order
        rX : list of Motors
            Motor objects associated with rX of each crystal, in order
            This is motion tangental to the rowland circle
        dy : list of numbers
            vertical offset of each crystal from the source, in order
        rZ : Motor
            Common rowland motion around the Rowland circle
        rDZ : Motor
            Detector motion around the Rowland circle
        hkl : tuple of int, optional
            crystal orientation
        elem : string, optional
            element of the crystals
        radius : number, optional
            radius of the Rowland circle
        """
        rowlands = OrderedDict()
        for name, chi, theta, z, y in zip(names, rChi, rTheta, rX, dy):
            rowlands[name] = RowlandSingle(chi, theta, z, y)
        self.crystals = RowlandGroup(rowlands)
        self._crystals = rowlands
        self.rZ = rZ
        self.rDZ = rDZ

        self.hkl = hkl
        self.elem = elem
        self.radius = radius
        self.dSpacing = 10**10 * calc.dSpace(self.elem, self.hkl) #ANGSTROMS

    def getPos(self, energy=None, printIt=True):
        """
        Get the calculated positions of rTheta, rZ, and rDZ for a particular
        energy, or the current energy. Energy is in eV.

        Parameters
        ----------
        energy : number, optional
            Photon energy in eV

        Returns
        -------
        pos : list of floats
            [rTheta, rZ, rDZ, X]
        """
        if energy is None:
            energy = self.getE()

        ## Calculate Bragg angle and the geometry.
        #angle = calc.asind(12398.52/(energy*2*self.dSpacing))
        #Z = self.radius*calc.sind(angle)
        #DZ = 2*self.radius*calc.cosd(angle)*calc.sind(angle)
        angle = calc.asind(12398.52/(energy*2*self.dSpacing))
        Z = self.radius*calc.sind(angle)*calc.cosd(angle)
        DZ = 2*Z
        X = self.radius*(calc.sind(angle)**2)

        if printIt:
            print "\n \t angle: \t %.3f" % angle
            print " \t Z: \t \t %.3f" % Z
            print " \t DZ: \t \t %.3f" % (DZ)
            print " \t X: \t \t %.3f\n" % X

        pos = [angle, Z, DZ, X]
        return pos

    def getE(self, angle=None, z=None, dz=None):
        """
        Calculate the energy at a particular angle, or the current angle.
        Energy is in eV.
        """
        if angle is None:
            #angle = self._crystals.values()[0].rTheta.wm()
            if dz is None:
                if z is None:
                    dz = self.rDZ.wm()
                else:
                    dz = 2*z
            angle = 90 - 0.5 * calc.asind(dz/self.radius)
        energy = 12398.52/calc.sind(angle)/2/self.dSpacing
        return energy

    def moveE(self, energy, debug=False):
        """
        Move the rTheta, rZ, rDZ motors to match a certain energy in eV.

        Parameters
        ----------
        energy : number
            Target energy in eV
        debug : bool, optional
            If True, print destinations but do not move.
        """
        pos = self.getPos(energy, printIt=False)
        #if not self._within_limits(*pos):
        if not self._within_limits(pos[1], pos[2], pos[3]):
            return
        for name, cr in self._crystals.items():
            if debug:
        #        print 'mv', name, 'rTheta from', cr.rTheta.wm(), 'to', pos[0]
                print 'mv', name, 'rX from', cr.rX.wm(), 'to', pos[3]
            else:
        #        cr.rTheta.mv(pos[0])
                cr.rX.mv(pos[3])
        if debug:
            print 'mv rZ from', self.rZ.wm(), 'to', pos[1]
            print 'mv rDZ from', self.rDZ.wm(), 'to', pos[2]
        else:
            self.rZ.mv(pos[1])
            self.rDZ.mv(pos[2])

    #def _within_limits(self, angle, z, dz, x):
    def _within_limits(self, z, dz, x):
        ok = True
        for name, cr in self._crystals.items():
            #if not cr.rTheta.within_limits(angle):
            #    ok = False
            if not cr.rX.within_limits(x):
                ok = False
        if not self.rZ.within_limits(z):
            ok = False
        if not self.rDZ.within_limits(dz):
            ok = False
        return ok

    def setE(self, energy):
        """
        Set current motor positions to match input energy in eV.
        Affects rZ, rDZ, and all rTheta

        Parameters
        ----------
        energy : number
            Current known energy of the motor positions.
        """
        pos = self.getPos(energy, printIt=False)
        for name, cr in self._crystals.items():
        #    cr.rTheta.set(pos[0])
            cr.rX.set(pos[3])
        self.rZ.set(pos[1])
        self.rDZ.set(pos[2])

    #def pointChi(self, y=0):
    #    """
    #    Adjust all chi motors such that the crystals point to a point at
    #    elevation y and distance radius+rX from the rowland stack.
    #    """
    #    pass # Is this needed?

    def wait(self):
        """
        Halt the thread until all Rowland motors are done moving.
        """
        for cr in self._crystals.values():
            cr.rChi.wait()
            cr.rTheta.wait()
            cr.rX.wait()
        self.rZ.wait()
        self.rDZ.wait()

    def status(self):
        """
        Print verbose information about the Rowland status.
        """
        print "Rowland Status:"
        print "Energy: {0} eV".format(self.getE())
        for name, cr in self._crystals.items():
            print name, "crystal:"
            print "rChi:   {0} deg".format(cr.rChi.wm())
            print "rTheta: {0} deg".format(cr.rTheta.wm())
            print "rX:     {0} mm".format(cr.rX.wm())
        print "rZ:     {0} mm".format(self.rZ.wm())
        print "rDZ:    {0} mm".format(self.rDZ.wm())


class RowlandGroup(object):
    """
    Tab-accessible group of repeated rowland motors
    """
    def __init__(self, rowlands={}):
        for name, rowland in rowlands.items():
            setattr(self, name, rowland)

class RowlandSingle(object):
    """
    Tab-accesible member of RowlandGroup
    """
    def __init__(self, rChi, rTheta, rX, dy):
        self.rChi = rChi
        self.rTheta = rTheta
        self.rX = rX
        self._dy = dy
