"""
Module to handle the FEE spectrometer.
"""
from blbase.motor import Motor

class FeeSpec(object):
    """
    Holds the motors in the FEE Spectrometer.
    May be expanded later to include more functionality.
    """
    def __init__(self, motors):
        for m in motors:
            setattr(self, m.name, m)

# It's very likely that there will only be one of these devices ever. Since we
# share PVs, I've instantiated it here so nobody has to repeat it elsewhere.
# "from feespec import feespec"
motors = []
pv = "STEP:FEE1:44{}:MOTR"
for i, name in zip(range(1, 8), ("crys_x", "crys_ang", "cam_ang", "cam_dist",
                                 "cam_iris", "filter", "cam_x")):
    motors.append(Motor(pv.format(i), name=name))
feespec = FeeSpec(motors)

