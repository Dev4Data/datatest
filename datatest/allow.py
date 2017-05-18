# -*- coding: utf-8 -*-
import inspect
from functools import wraps
from math import isnan
from numbers import Number
from .utils.builtins import *
from .utils import collections
from .utils import functools
from .utils import itertools

from .dataaccess import _is_collection_of_items
from .dataaccess import DictItems
from .errors import ValidationError

from .utils.misc import _is_consumable
from .utils.misc import _is_nsiterable
from .utils.misc import _get_arg_lengths
from .utils.misc import _expects_multiple_params
from .utils.misc import _make_decimal
from .errors import Missing
from .errors import Extra
from .errors import Deviation


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


def _is_mapping_type(obj):
    return isinstance(obj, collections.Mapping) or \
                _is_collection_of_items(obj)


class BaseAllowance(object):
    """Context manager to allow differences without triggering a
    test failure. *filterfalse* should accept a predicate and an
    iterable of data errors and return an iterable of only those
    errors which are **not** allowed.
    """
    def __init__(self, filterfalse, predicate, msg=None):
        """Initialize object values."""
        assert callable(filterfalse)
        assert callable(predicate) or predicate is None

        self.filterfalse = filterfalse
        self.predicate = predicate
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # Apply filterfalse or reraise non-validation error.
        if issubclass(exc_type, ValidationError):
            errors = self.filterfalse(self.predicate, exc_value.errors)
        elif exc_type is None:
            errors = self.filterfalse(self.predicate, [])
        else:
            raise exc_value

        # Check container types.
        mappable_in = _is_mapping_type(exc_value.errors)
        mappable_out = _is_mapping_type(errors)

        # Check if any errors were returned.
        try:
            first_item = next(iter(errors))
            if _is_consumable(errors):  # Rebuild if consumable.
                errors = itertools.chain([first_item], errors)
        except StopIteration:
            return True  # <- EXIT!

        # Handle mapping input with iterable-of-items output.
        if (mappable_in and not mappable_out
                and isinstance(first_item, collections.Sized)
                and len(first_item) == 2):
            errors = DictItems(errors)
            mappable_out = True

        # Verify type compatibility.
        if mappable_in != mappable_out:
            message = ('{0} received {1!r} collection but '
                       'returned incompatible {2!r} collection')
            filter_name = getattr(self.filterfalse, '__name__',
                                  repr(self.filterfalse))
            output_cls = errors.__class__.__name__
            input_cls = exc_value.errors.__class__.__name__
            raise TypeError(message.format(filter_name, input_cls, output_cls))

        # Re-raise ValidationError() with remaining errors.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)
        exc = ValidationError(message, errors)
        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


def getvalue(function):
    def adapted(key, value):  # <- key not used.
        return function(value)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getvalue
    return adapted


def getargs(function):
    def adapted(key, value):  # <- key not used.
        return function(*value.args)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getargs
    return adapted


def getkey(function):
    def adapted(key, value):  # <- value not used.
        if _is_nsiterable(key):
            return function(*key)
        return function(key)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getkey
    return adapted


def getpair(function):
    def adapted(key, value):
        return function(key, value)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getpair
    return adapted


def pairwise_filterfalse(predicate, iterable):
    """Make an iterator that filters elements from *iterable*
    returning only those for which the *predicate* is False. The
    *predicate* must be a function of two arguments (key and value).
    """
    if isinstance(iterable, collections.Mapping):
        iterable = getattr(iterable, 'iteritems', iterable.items)()

    if _is_collection_of_items(iterable):
        for key, value in iterable:
            if (not _is_nsiterable(value)
                    or isinstance(value, Exception)
                    or isinstance(value, collections.Mapping)):
                if not predicate(key, value):
                    yield key, value
            else:
                values = list(v for v in value if not predicate(key, v))
                if values:
                    yield key, values
    else:
        for value in iterable:
            if not predicate(None, value):
                yield value


class allow_pair(BaseAllowance):
    """Accepts a *function* of two arguments (key and error)."""
    def __init__(self, function, msg=None):
        super(allow_pair, self).__init__(pairwise_filterfalse, function, msg)


class allow_error(BaseAllowance):
    """Accepts a *function* of one argument."""
    def __init__(self, function, msg=None):
        @wraps(function)
        def wrapped(_, value):
            return function(value)
        super(allow_error, self).__init__(pairwise_filterfalse, wrapped, msg)


class allow_missing(allow_error):
    def __init__(self, msg=None):
        def is_missing(value):
            return isinstance(value, Missing)
        super(allow_missing, self).__init__(is_missing, msg)


class allow_extra(allow_error):
    def __init__(self, msg=None):
        def is_extra(value):
            return isinstance(value, Extra)
        super(allow_extra, self).__init__(is_extra, msg)


def _prettify_devsig(method):
    """Prettify signature of deviation __init__ classes by patching
    its signature to make the "tolerance" syntax the default option
    when introspected (with an IDE, REPL, or other user interface).
    This helper function is intended for internal use.
    """
    assert method.__name__ == '__init__'
    try:
        signature = inspect.signature(method)
    except AttributeError:  # Not supported in Python 3.2 or older.
        return  # <- EXIT!

    parameters = [
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('kwds_func', inspect.Parameter.VAR_KEYWORD),
    ]
    method.__signature__ = signature.replace(parameters=parameters)


def _normalize_devargs(lower, upper, funcs):
    """Normalize deviation allowance arguments to support both
    "tolerance" and "lower, upper" signatures. This helper function
    is intended for internal use.
    """
    if callable(upper):
        funcs = (upper,) + funcs
        upper = None

    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance
    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    assert lower <= upper
    return (lower, upper, funcs)


class allow_deviation(allow_error):
    """
    allow_deviation(tolerance, /, msg=None)
    allow_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, funcs = _normalize_devargs(lower, upper, ())
        def tolerance(error):  # <- Closes over lower & upper.
            deviation = error.deviation or 0.0
            if isnan(deviation) or isnan(error.expected or 0.0):
                return False
            return lower <= deviation <= upper
        super(allow_deviation, self).__init__(tolerance, msg)
_prettify_devsig(allow_deviation.__init__)


class allow_percent_deviation(allow_error):
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, funcs = _normalize_devargs(lower, upper, ())
        def percent_tolerance(error):  # <- Closes over lower & upper.
            percent_deviation = error.percent_deviation
            if isnan(percent_deviation) or isnan(error.expected or 0):
                return False
            return lower <= percent_deviation <= upper
        super(allow_percent_deviation, self).__init__(percent_tolerance, msg)
_prettify_devsig(allow_percent_deviation.__init__)


class allow_specified(BaseAllowance):
    def __init__(self, errors, msg=None):
        if _is_collection_of_items(errors):
            errors = dict(errors)
        elif isinstance(errors, Exception):
            errors = [errors]

        def grpfltrfalse(allowed, iterable):
            if isinstance(iterable, Exception):
                iterable = [iterable]

            if isinstance(allowed, Exception):
                allowed = [allowed]
            else:
                allowed = list(allowed)  # Make list or copy existing list.

            for x in iterable:
                try:
                    allowed.remove(x)
                except ValueError:
                    yield x

            if allowed:  # If there are left-over errors.
                message = 'allowed errors not found: {0!r}'
                exc = Exception(message.format(allowed))
                exc.__cause__ = None
                yield exc

        def filterfalse(_, iterable):
            if isinstance(iterable, collections.Mapping):
                iterable = getattr(iterable, 'iteritems', iterable.items)()

            if _is_collection_of_items(iterable):
                if isinstance(errors, collections.Mapping):
                    for key, group in iterable:
                        try:
                            errors_lst = errors[key]
                            result = list(grpfltrfalse(errors_lst, group))
                            if result:
                                yield key, result
                        except KeyError:
                            yield key, group
                else:
                    errors_lst = list(errors)  # Errors must not be consumable.
                    for key, group in iterable:
                        result = list(grpfltrfalse(errors_lst, group))
                        if result:
                            yield key, result
            else:
                if not _is_mapping_type(errors):
                    for x in grpfltrfalse(errors, iterable):
                        yield x
                else:
                    message = ('{0!r} of errors cannot be matched using {1!r} '
                               'of allowances, requires non-mapping type')
                    message = message.format(iterable.__class__.__name__,
                                             errors.__class__.__name__)
                    raise ValueError(message)

        super(allow_specified, self).__init__(filterfalse, None, msg)


class allow_limit(BaseAllowance):
    def __init__(self, number, *funcs, **kwds):
        normalize = lambda f: f if hasattr(f, '_decorator') else getvalue(f)
        funcs = tuple(normalize(f) for f in funcs)

        def grpfltrfalse(key, group):
            group = iter(group)  # Must be consumable.
            matching = []
            for value in group:
                if all(f(key, value) for f in funcs):  # Closes over 'funcs'.
                    matching.append(value)
                    if len(matching) > number:  # Closes over 'number'.
                        break
                else:
                    yield value
            # If number is exceeded, return all errors.
            if len(matching) > number:
                for value in itertools.chain(matching, group):
                    yield value

        def filterfalse(_, iterable):
            if isinstance(iterable, collections.Mapping):
                iterable = getattr(iterable, 'iteritems', iterable.items)()

            if _is_collection_of_items(iterable):
                for key, group in iterable:
                    if (not _is_nsiterable(group)
                            or isinstance(group, Exception)
                            or isinstance(group, collections.Mapping)):
                        group = [group]
                    value = list(grpfltrfalse(key, group))
                    if value:
                        yield key, value
            else:
                for f in funcs:  # Closes over 'funcs'.
                    if f._decorator != getvalue:
                        message = 'cannot use {0!r} decorator with {1!r} of errors'
                        dec_name = f._decorator.__name__
                        itr_type = iterable.__class__.__name__
                        raise ValueError(message.format(dec_name, itr_type))

                for value in grpfltrfalse(None, iterable):
                    yield value

        super(allow_limit, self).__init__(filterfalse, None, **kwds)
