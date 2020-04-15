"""
Module for organizing objects in the beamline.

Contains utilities for grouping objects together in beamline.py to satisfy
the individual needs of each hutch without compromising code unification.
"""
import functools
import inspect
import importlib
from blutil.doctools import argspec

class SimpleContainer(object):
    """
    Object that contains other objects as its attributes. It's a box.
    """
    def __init__(self, **objs):
        """
        Objs are key=value pairs to start in the box.
        """
        for k, v in objs.items():
            setattr(self, k, v)

def alias_class(Class, **aliases):
    """
    Make a second version of Class that has aliased attribute names.
    **aliases are old=new key value pairs, where old must be a string and new
        can either be a string or a list/tuple of strings.
    Attribute names that are omitted will carry through unaliased.
    """
    def proxy_class(*args):
        obj = alias_object(Class(*args))
        return alias_object(obj, **aliases)
    proxy_class.__doc__ = argspec(Class.__init__) + "\n" + Class.__doc__
    return proxy_class

def alias_object(obj, **aliases):
    """
    Make a linked copy of obj that has aliased attribute names.
    **aliases are old=new key value pairs, where old must be a string and new
        can either be a string or a list/tuple of strings.
    Attribute names that are omitted will carry through unaliased.
    """
    attrs = {}
    attrs["__doc__"] = obj.__doc__
    attrs["__module__"] = obj.__class__.__module__
    for a in object_attrs(obj):
        name = aliases.get(a, a)
        if isinstance(name, (list, tuple)):
            for n in name:
                attrs[n] = proxy_property(obj, a)
        else:
            attrs[name] = proxy_property(obj, a)
    AliasClass = type(obj.__class__.__name__, (object,), attrs)
    return AliasClass()

def object_merge(name, *objs):
    """
    Create and instantiate a merged object.

    Merged objects have the attributes that their constituent objects have,
    and forward all getattr, setattr, delattr requests to the original object.
    """
    attrs = {}
    doc = "Docstrings of merged objects:"
    for obj in objs:
        try:
            doc += "\n" + obj.__doc__
        except:
            pass
        for a in object_attrs(obj):
            attrs[a] = proxy_property(obj, a)
    attrs["__doc__"] = doc
    MergeClass = type(name, (object,), attrs)
    return MergeClass()

def proxy_property(obj, attr):
    """
    Create a property object that behaves like attr from obj.
    When accessed, forwards all getattr, setattr, delattr requests to obj.
    Sets up a clean, useful docstring for ipython sessions.
    """
    def optattr(func, obj, attr, self, *args):
        return func(obj, attr, *args)
    parts = [functools.partial(optattr, f, obj, attr) for f in (getattr, setattr, delattr)]
    property_no_doc = type("property", (property,), {})
    prop = property_no_doc(*parts)
    v = getattr(obj, attr)
    doc = ""
    if callable(v):
        doc += argspec(v) + "\n"
    if hasattr(v, "__dict__"):
        try:
            doc += v.__doc__
        except:
            pass
    else:
        doc += "type " + v.__class__.__name__
    prop.__doc__ = doc
    return prop

def object_attrs(obj):
    """
    Return a list of valid object attributes. Ignore double underscores.
    """
    keys = obj.__class__.__dict__.keys() + obj.__dict__.keys()
    return [k for k in keys if k[:2] != "__"]

