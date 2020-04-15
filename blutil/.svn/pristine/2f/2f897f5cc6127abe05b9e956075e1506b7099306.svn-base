from __future__ import print_function
import os
from blbase.motor import Motor
from blbase.motorsfile import Motors
from blutil import printnow

class BaseExperiment(object):
    """
    Base class for Experiment objects to define common features.

    Parameters
    ----------
    expname : string, optional
        Name of the experiment

    elog : pswww.pypsElog.pypsElog, optional
        Elog object to post to the electronic logbook
    """
    def __init__(self, **kwargs):
        self.elog = kwargs.get("elog")
        self.expname = kwargs.get("expname", "default")

    def elog(self, comment=""):
        """
        Post current experiment status to elog, with optional comment.

        Parameters
        ----------
        comment : string, optional
            comment for the elog posting
        """
        if self.elog is None:
            print("No elog argument passed to Experiment object!")
        else:
            if (comment != ""): comment += "\n"
            self.elog.submit(comment + self.status(do_print=False))

    def status(self, do_print=True):
        """
        Print or return a status string. This should be subclassed for
        experiment or hutch-specific statuses.

        Parameters
        ----------
        do_print : bool, optional
            If True, print the status. If False, return it as a string.

        Returns
        -------
        status : string or None
        """
        txt = ""
        if do_print:
            print(txt)
        else:
            return txt

    def __repr__(self):
        return "<{} experiment object>".format(self.expname)

class EpicsArchMotorsExp(BaseExperiment):
    """
    Experiment that imports motors from an EpicsArch file.

    Parameters
    ----------
    arch_dir : string
        directory containing the epicsArch files

    arch_files : string or list of strings
        files in arch_dir to include

    expname : string, optional
        name of the experiment

    elog : pswww.pypsElog.pypsElog, optional
        Elog object to post to the electronic logbook

    motors_obj : blbase.motorsfile.Motors or object or list of such, optional
        object that groups motors together

    use_existing : bool, optional
        If True, use existing Motor objects from motors_obj when applicable
        rather than creating duplicate Motor objects with new names.
    """
    def __init__(self, **kwargs):
        super(EpicsArchMotorsExp, self).__init__(**kwargs)
        arch_dir = kwargs["arch_dir"]
        arch_files = kwargs["arch_files"]
        motors_obj = kwargs.get("motors_obj")
        use_existing = kwargs.get("use_existing", False)
        if not isinstance(arch_files, list):
            arch_files = [arch_files]
        if not isinstance(motors_obj, list):
            motors_obj = [motors_obj]

        self._motors = None
        other_motors = []

        for obj in motors_obj:
            if isinstance(obj, Motors) and self._motors is None:
                self._motors = obj
                continue
            else:
                other_motors.append(obj)
        if self._motors is None:
            self._motors = Motors()

        if use_existing:
            all_motors = []
            for m in [self._motors] + other_motors:
                if isinstance(m, Motors):
                    all_motors.extend(m.all.get_motors())
                else:
                    all_motors.extend([n for n in m.__dict__.values()
                                       if isinstance(n, Motor)])

        try:
            printnow("Importing motors from ")
            for file in arch_files:
                printnow(file + "... ")
                full_path = os.path.join(arch_dir, file)
                if use_existing:
                    group = self._motors.import_epicsArch(full_path,
                        skip_import=all_motors)
                else:
                    group = self._motors.import_epicsArch(full_path)
                self._motors.groups.add("user", *group.get_motors())
            user_motors = self._motors.groups.user.get_motors()
            for motor in user_motors:
                setattr(self, motor.name, motor)
                for group in other_motors:
                    if isinstance(group, Motors):
                        group.add(motor, group="user")
                    else:
                        setattr(group, motor.name, motor)
            print("done")
        except Exception as exc:
            print("Importing from epicsArch failed!")
            print(exc)

