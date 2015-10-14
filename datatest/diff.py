# -*- coding: utf-8 -*-
from ._decimal import Decimal as _Decimal


def _make_decimal(d):
    if isinstance(d, float):
        d = str(d)
    d = _Decimal(d)

    if d == d.to_integral():             # Remove_exponent (from official
        return d.quantize(_Decimal(1))   # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


class ItemBase(object):
    def __init__(self, item, **kwds):
        self.item = item
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1!r}{2})'.format(clsname, self.item, kwds)

    def __hash__(self):
        return hash((self.__class__, self.__repr__()))

    def __eq__(self, other):
        return hash(self) == hash(other)

    @staticmethod
    def _format_kwds(kwds):
        if not kwds:
            return ''  # <- EXIT!
        kwds = sorted(kwds.items())
        try:
            kwds = [(k, unicode(v)) for k, v in kwds]  # Only if `unicode` is defined.
        except NameError:
            pass
        kwds = ['{0}={1!r}'.format(k, v) for k, v in kwds]
        kwds = ', '.join(kwds)
        return ', ' + kwds


class ExtraItem(ItemBase):
    pass


class MissingItem(ItemBase):
    pass


class InvalidItem(ItemBase):
    def __init__(self, item, expected=None, **kwds):
        self.item = item
        self.expected = expected
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.expected == None:
            expected = ''
        else:
            expected = ', ' + repr(self.expected)
        return '{0}({1!r}{2}{3})'.format(clsname, self.item, expected, kwds)


class InvalidNumber(ItemBase):
    def __init__(self, diff, expected, **kwds):
        if not diff:
            raise ValueError('diff must be positive or negative number')
        self.diff = _make_decimal(diff)
        if expected != None:
            expected = _make_decimal(expected)
        self.expected = expected
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        diff = '{0:+}'.format(self.diff)  # Apply +/- sign.
        return '{0}({1}, {2}{3})'.format(clsname, diff, self.expected, kwds)


class NonStrictRelation(ItemBase):
    """Base class for to indicate non-strict subset or superset relationships."""
    def __init__(self, **kwds):
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1})'.format(clsname, kwds)


class NotProperSubset(NonStrictRelation):
    pass


class NotProperSuperset(NonStrictRelation):
    pass
