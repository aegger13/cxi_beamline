"""
Module for working with doc strings
"""
import inspect
from types import MethodType

"""
doc_inherit

Inspired by http://code.activestate.com/recipes/576862/
Simplified the code while improving functionality.

Quick note on how this works and why it's set up this way:

When we do @doc_inherit before a def statement in a class, we're replacing
the defined function with doc_inherit(func), an instance of doc_inherit.
Later, when we want to access this function, the doc_inherit object runs
__get__ and returns the properly constructed method instead of returning
itself, and then we can call the method as is but with an augmented doc string.

We do this in a funky way using a class instead of nested functions because:
1. You cannot check what a method's parent is before it is tied to a class.
    This doesn't happen until AFTER the full class definition.
2. You cannot change the docstring of a class method.

So we store the function instead of binding it, planning to change the
docstring later. When we need the function for the first time, we find the
correct source docstring, apply it to the function, then return it as a
MethodType so it looks and acts 100% normal.
"""
class doc_inherit(object):
    """
    Method decorator to inherit a docstring from the parent class.
    Prepends a method's docstring with the parent method's full docstring.
    """
    def __init__(self, method):
        """
        @doc_inherit replaces method with doc_inherit(method)
        """
        self.method = method
        self.doc_string = None

    def __get__(self, obj, cls):
        """
        Return a bound or unbound method with the correct docstring when we
        get our object (instead of returning a doc_inherit object)
        """
        if self.doc_string is None:
            for parent in cls.mro()[1:]:
                source = getattr(parent, self.method.__name__, None)
                if source: break
            if source is None:
                err = "doc_inherit could not find '{}' in parent"
                err = err.format(self.method.__name__)
                raise NameError(err)
            method_doc = getattr(self.method, "__doc__", "") or ""
            self.doc_string = source.__doc__ + method_doc
        self.method.__doc__ = self.doc_string
        return MethodType(self.method, obj, cls)


def argspec(func):
    """
    Return a string that looks like the func's definition line.
    example:
    In [1] def func(arg1, arg2=0, *args, **kwargs):
               pass
    In [2] argspec(func)
    Out[2] "func(arg1, arg2=0, *args, **kwargs)"
    """
    spec = inspect.getargspec(func)
    argnames = spec[0]
    defaults = spec[3]
    args = []
    for i in range(len(argnames)):
        j = -(i + 1)
        arg = argnames[j]
        try:
            arg += "=" + defaults[j].__name__
        except:
            try:
                arg += "=" + str(defaults[j])
            except:
                pass
        args.insert(0, arg)
    if spec[1] is not None:
        args.append("*" + spec[1])
    if spec[2] is not None:
        args.append("**" + spec[2])
    txt = func.__name__ + "(" + ", ".join(args) + ")"
    return txt

