"""
Generic goniometer class.

Groups goniometer motors and calculations together in a container.
"""

class Gon(object):
    """
    Object to group goniometer motors and common alignment calculations
    """
    def __init__(self, **motors):
        for name, mot in motors.items():
            setattr(self, name, mot)
        self.calc = GonCalc()

class GonCalc(object):
    """
    Collection of calculations useful when setting up a goniometer
    """
    def center_of_rotation(self, pt1, pt2, pt3):
        try:
            return _center_of_rotation(pt1, pt2, pt3)
        except TypeError, exc:
            print "TypeError: {}".format(exc)

def _center_of_rotation(pt1, pt2, pt3):
    """
    Given three points in a plane, finds the center of the circle that
    intersects all three points. Raises an error if the three points are
    collinear.

    pt1, pt2, pt3: tuples or lists with two elements (x, y), a point.
    """
    if pt1 == pt2 or pt2 == pt3 or pt1 == pt3:
        raise TypeError("Need three unique points.")
    pt1 = _Point(pt1[0], pt1[1])
    pt2 = _Point(pt2[0], pt2[1])
    pt3 = _Point(pt3[0], pt3[1])
    pt_12 = _midpt(pt1, pt2)
    pt_23 = _midpt(pt2, pt3)
    slope_12 = _slope(pt1, pt2)
    slope_23 = _slope(pt2, pt3)
    if slope_12 == slope_23:
        raise TypeError("All three points are collinear, no circle.")
    if slope_12 == 0:
        perp_12 = _Line(pt_12, float("inf"))
    else:
        perp_12 = _Line(pt_12, -1/slope_12)
    if slope_23 == 0:
        perp_23 = _Line(pt_23, float("inf"))
    else:
        perp_23 = _Line(pt_23, -1/slope_23)
    answer = _intersection(perp_12, perp_23)
    return (answer.x, answer.y)

class _Point(object):
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

def _midpt(pt1, pt2):
    return _Point((pt1.x + pt2.x)/2., (pt1.y + pt2.y)/2.)

def _slope(pt1, pt2):
    try:
        return float((pt2.y - pt1.y)/(pt2.x - pt1.x))
    except ZeroDivisionError:
        return float("inf")

class _Line(object):
    def __init__(self, pt, slope):
        self.slope = slope
        self.yintercept = pt.y - slope * pt.x
        self.pt = pt

def _intersection(line1, line2):
    if line1.slope == float("inf"):
        x = line1.pt.x
        y = line2.slope * x + line2.yintercept
    elif line2.slope == float("inf"):
        x = line2.pt.x
        y = line1.slope * x + line1.yintercept
    else:
        x = (line2.yintercept - line1.yintercept) / (line1.slope - line2.slope)
        y = line1.slope * x + line1.yintercept
    return _Point(x, y) 

