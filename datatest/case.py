# -*- coding: utf-8 -*-
from __future__ import division

import inspect
import pprint
from unittest import TestCase

from datatest.diff import DiffBase
from datatest.diff import ExtraColumn
from datatest.diff import ExtraValue
from datatest.diff import ExtraSum
from datatest.diff import MissingColumn
from datatest.diff import MissingValue
from datatest.diff import MissingSum


class DataAssertionError(AssertionError):
    """Data assertion failed."""
    def __init__(self, msg, diff):
        """Initialize self, store difference for later reference."""
        if not diff:
            raise ValueError('Missing difference.')
        self.diff = diff
        self.msg = msg
        return AssertionError.__init__(self, msg)

    def __repr__(self):
        return self.__class__.__name__ + ': ' + self.__str__()

    def __str__(self):
        diff = pprint.pformat(self.diff, width=1)
        if any([diff.startswith('{') and diff.endswith('}'),
                diff.startswith('[') and diff.endswith(']'),
                diff.startswith('(') and diff.endswith(')')]):
            diff = diff[1:-1]
        return '{0}:\n {1}'.format(self.msg, diff)


def _walk_diff(diff):
    """Iterate over difference or collection of differences."""
    if isinstance(diff, dict):
        diff = diff.values()
    elif isinstance(diff, DiffBase):
        diff = (diff,)

    for item in diff:
        if isinstance(item, (dict, list, tuple)):
            for elt2 in _walk_diff(item):
                yield elt2
        else:
            if not isinstance(item, DiffBase):
                raise TypeError('Object {0!r} is not derived from DiffBase.'.format(item))
            yield item


class _BaseAcceptContext(object):
    def __init__(self, accepted, test_case, callable_obj=None):
        self.accepted = accepted
        self.test_case = test_case
        if callable_obj is not None:
            try:
                self.obj_name = callable_obj.__name__
            except AttributeError:
                self.obj_name = str(callable_obj)
        else:
            self.obj_name = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        raise NotImplementedError()

    def _raiseFailure(self, standardMsg, difference):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        try:
            # For Python 3.x (some 3.2 builds will raise a TypeError
            # while 2.x will raise SyntaxError).
            expr = 'raise DataAssertionError(msg, {0}) from None'
            exec(expr.format(repr(difference)))
        except (SyntaxError, TypeError):
            raise DataAssertionError(msg, difference)  # For Python 2.x

    def handle(self, name, callable_obj, args, kwargs):
        """If callable_obj is None, assertRaises/Warns is being used as
        a context manager, so check for a 'msg' kwarg and return self.
        If callable_obj is not None, call it passing args and kwargs.

        """
        if callable_obj is None:
            self.msg = kwargs.pop('msg', None)
            return self
        with self:
            callable_obj(*args, **kwargs)


class _AcceptDifferenceContext(_BaseAcceptContext):
    def __exit__(self, exc_type, exc_value, tb):
        difference = list(_walk_diff(exc_value.diff))
        accepted = list(_walk_diff(self.accepted))
        unaccepted = [x for x in difference if x not in accepted]
        if unaccepted:
            return self._raiseFailure(exc_value.msg, unaccepted)  # <- EXIT!

        accepted_not_found = [x for x in accepted if x not in difference]
        if accepted_not_found:
            message = exc_value.msg + ', accepted difference not found'
            return self._raiseFailure(message, accepted_not_found)  # <- EXIT!

        return True


class _AcceptAbsoluteToleranceContext(_BaseAcceptContext):
    def __init__(self, accepted, test_case, callable_obj=None):
        assert accepted >= 0, 'Tolerance cannot be defined with a negative number.'
        _BaseAcceptContext.__init__(self, accepted, test_case, callable_obj)

    def __exit__(self, exc_type, exc_value, tb):
        difference = list(_walk_diff(exc_value.diff))
        accepted = self.accepted

        failed = []
        for diff in difference:
            if abs(diff.diff) > accepted:
                failed.append(diff)
        if failed:
            return self._raiseFailure(exc_value.msg, failed)  # <- EXIT!

        return True


class _AcceptPercentToleranceContext(_BaseAcceptContext):
    def __init__(self, accepted, test_case, callable_obj=None):
        assert 1 >= accepted >= 0, 'Percent tolerance must be between 0 and 1.'
        _BaseAcceptContext.__init__(self, accepted, test_case, callable_obj)

    def __exit__(self, exc_type, exc_value, tb):
        difference = list(_walk_diff(exc_value.diff))
        accepted = self.accepted

        failed = []
        for diff in difference:
            percent = diff.diff / diff.sum
            if abs(percent) > accepted:
                failed.append(diff)
        if failed:
            return self._raiseFailure(exc_value.msg, failed)  # <- EXIT!

        return True


class DataTestCase(TestCase):
    tolerance = None
    #absoluteTolerance = None
    #percentTolerance = None

    def __getattr__(self, name):
        if name in ('trustedData', 'subjectData'):
            for record in inspect.stack():  # Bubble-up stack looking
                frame = record[0]           # for data source.
                if name in frame.f_globals:
                    return frame.f_globals[name]  # <- EXIT!
            raise NameError('name {0!r} is not defined'.format(name))
        else:
            obj = repr(self.__class__.__name__)
            attr = repr(name)
            message = '{0} object has no attribute {1}'.format(obj, attr)
            raise AttributeError(message)

    def fail(self, msg, diff=None):
        """Fail immediately, record failures, with the given message."""
        if diff:
            raise DataAssertionError(msg, diff)
        else:
            raise self.failureException(msg)

    def acceptDifference(self, diffs, callableObj=None, *args, **kwargs):
        context = _AcceptDifferenceContext(diffs, self, callableObj)
        return context.handle('acceptDifference', callableObj, args, kwargs)

    def acceptTolerance(self, absolute=None, callableObj=None, *args, **kwargs):
        percent = kwargs.get('percent')

        _abs = absolute is not None
        _pct = percent is not None
        msg = 'Must provide absolute or percent tolerance (but not both).'
        assert (_abs or _pct) and not (_abs and _pct), msg

        if absolute:
            context = _AcceptAbsoluteToleranceContext(absolute, self, callableObj)
        else:
            context = _AcceptPercentToleranceContext(percent, self, callableObj)
        return context.handle('acceptTolerance', callableObj, args, kwargs)

    def assertColumnSet(self, msg=None):
        """Assert set of subject columns equal to set of trusted columns."""
        subject = set(self.subjectData.columns())
        trusted = set(self.trustedData.columns())
        if subject != trusted:
            extra = [ExtraColumn(x) for x in subject - trusted]
            missing = [MissingColumn(x) for x in trusted - subject]
            if msg is None:
                msg = 'different column names'
            self.fail(msg, extra+missing)

    def assertColumnSubset(self, msg=None):
        """Assert that set of subject columns is subset of trusted columns."""
        subject = set(self.subjectData.columns())
        trusted = set(self.trustedData.columns())
        if not subject.issubset(trusted):
            extra = subject.difference(trusted)
            extra = [ExtraColumn(x) for x in extra]
            if msg is None:
                msg = 'different column names'  # found extra columns
            self.fail(msg, extra)

    def assertColumnSuperset(self, msg=None):
        """Assert that set of subject columns is superset of trusted columns."""
        trusted = set(self.trustedData.columns())
        subject = set(self.subjectData.columns())
        if not subject.issuperset(trusted):
            missing = trusted.difference(subject)
            missing = [MissingColumn(x) for x in missing]
            if msg is None:
                msg = 'different column names'  # missing expected columns
            self.fail(msg, missing)

    def assertValueSet(self, column, msg=None, **kwds):
        """Assert that set of subject values is equal to trusted values."""
        trusted = self.trustedData.set(column, **kwds)
        subject = self.subjectData.set(column, **kwds)
        if subject != trusted:
            extra = [ExtraValue(x) for x in subject - trusted]
            missing = [MissingValue(x) for x in trusted - subject]
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, extra+missing)

    def assertValueSubset(self, column, msg=None, **kwds):
        """Assert that set of subject values is subset of trusted values."""
        trusted = self.trustedData.set(column, **kwds)
        subject = self.subjectData.set(column, **kwds)
        if not subject.issubset(trusted):
            extra = subject.difference(trusted)
            extra = [ExtraValue(x) for x in extra]
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, extra)

    def assertValueSuperset(self, column, msg=None, **kwds):
        """Assert that set of subject values is superset of trusted values."""
        trusted = self.trustedData.set(column, **kwds)
        subject = self.subjectData.set(column, **kwds)
        if not subject.issuperset(trusted):
            missing = trusted.difference(subject)
            missing = [MissingValue(x) for x in missing]
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, missing)

    def assertValueSum(self, column, groups, msg=None, **kwds):
        """Assert that sums of subject match sums of trusted."""
        trusted = self.trustedData
        subject = self.subjectData

        def test(group_kwds):
            subject_sum = subject.sum(column, **group_kwds)
            trusted_sum = trusted.sum(column, **group_kwds)
            tolerance = self.tolerance if self.tolerance else 0
            s_sum = subject_sum if subject_sum else 0
            t_sum = trusted_sum if trusted_sum else 0
            difference = s_sum - t_sum
            try:
                assert abs(difference) <= tolerance  # <- The assertion!
            except AssertionError:
                all_kwds = kwds.copy()
                all_kwds.update(group_kwds)
                if difference > 0:
                    return ExtraSum(difference, t_sum, **all_kwds)
                else:
                    return MissingSum(difference, t_sum, **all_kwds)
            return None

        failures = [test(x) for x in trusted.groups(*groups, **kwds)]
        failures = [x for x in failures if x != None]  # Filter for failures.
        if failures:
            if not msg:
                msg = 'different {0!r} sums'.format(column)
            self.fail(msg=msg, diff=failures)

