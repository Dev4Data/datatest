# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.diff import ItemBase
from datatest.diff import ExtraItem
from datatest.diff import MissingItem
from datatest.diff import InvalidNumber


class TestItemBase(unittest.TestCase):
    def test_repr(self):
        item = ItemBase('foo')
        self.assertEqual(repr(item), "ItemBase('foo')")

        item = ItemBase(item='foo')  # As kwds.
        self.assertEqual(repr(item), "ItemBase('foo')")

        item = ItemBase('foo', col4='bar')  # Using kwds for filtering.
        self.assertRegex(repr(item), "ItemBase\(u?'foo', col4=u?'bar'\)")

    def test_str(self):
        diff = ItemBase('foo', col4='bar')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = ItemBase('foo')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = ItemBase('foo')
        diff2 = ItemBase('foo')
        self.assertEqual(diff1, diff2)

        diff1 = ItemBase('foo')
        diff2 = ItemBase('bar')
        self.assertNotEqual(diff1, diff2)

        diff1 = ItemBase('foo')
        diff2 = "ItemBase('foo')"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = ItemBase('someval')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = ItemBase('someval', col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


class TestExtraAndMissing(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(ExtraItem, ItemBase))
        self.assertTrue(issubclass(MissingItem, ItemBase))


class TestInvalidNumber(unittest.TestCase):
    """Test InvalidNumber."""
    def test_instantiation(self):
        InvalidNumber(1, 100)  # Pass without error.

    def test_repr(self):
        diff = InvalidNumber(1, 100)  # Simple.
        self.assertEqual("InvalidNumber(+1, 100)", repr(diff))

        diff = InvalidNumber(-1, 100)  # Simple negative.
        self.assertEqual("InvalidNumber(-1, 100)", repr(diff))

        diff = InvalidNumber(3, 50, col1='a', col2='b')  # Using kwds.
        self.assertRegex(repr(diff), "InvalidNumber\(\+3, 50, col1=u?'a', col2=u?'b'\)")

    def test_str(self):
        diff = InvalidNumber(5, 75, col1='a')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = InvalidNumber(1, 100, col1='a', col2='b')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = InvalidNumber(1, 100)
        diff2 = InvalidNumber(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1.0, 100.0)
        diff2 = InvalidNumber(1.0, 100.0)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1.0, 100)
        diff2 = InvalidNumber(1,   100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100.0)
        diff2 = InvalidNumber(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100, foo='aaa', bar='bbb')
        diff2 = InvalidNumber(1, 100, bar='bbb', foo='aaa')
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100)
        diff2 = InvalidNumber(1, 250)
        self.assertNotEqual(diff1, diff2)

        diff1 = InvalidNumber(+1, 100)
        diff2 = "InvalidNumber(+1, 100)"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = InvalidNumber(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = InvalidNumber(-1, 100, col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval
