# -*- coding: utf-8 -*-
"""Test __past__.api_dev2 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
import re
from . import _io as io
from . import _unittest as unittest
from datatest.utils.decimal import Decimal

from .common import MinimalSource
import datatest
from datatest.__past__ import api_dev2  # <- MONKEY PATCH!!!

from datatest import DataError
from datatest import Missing
from datatest import Extra
from datatest import Invalid
from datatest import Deviation
from datatest import CsvSource
from datatest import DataTestCase
from datatest import CompareSet


class TestNamesAndAttributes(unittest.TestCase):
    def _run_wrapped_test(self, case, method):
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        result = runner.run(audit_case)

        error = result.errors[0][1] if result.errors else None
        failure = result.failures[0][1] if result.failures else None
        return error, failure

    def test_names(self):
        """In the 0.7.0 API, the assertEqual() method should be wrapped
        in a datatest.DataTestCase method of the same name.
        """
        # TODO: Add this check once the class has been renamed.
        # Check for DataTestCase name (now TestCase).
        #self.assertTrue(hasattr(datatest, 'DataTestCase'))

        # Check that wrapper exists.
        datatest_eq = datatest.DataTestCase.assertEqual
        unittest_eq = unittest.TestCase.assertEqual
        self.assertIsNot(datatest_eq, unittest_eq)

    def test_assertEqual(self):
        """Test for 0.7.0 assertEqual() wrapper behavior."""
        class _TestWrapper(datatest.DataTestCase):
            def test_method(_self):
                first = set([1, 2, 3])
                second = set([1, 2, 3, 4])
                with self.assertRaises(datatest.DataError) as cm:
                    _self.assertEqual(first, second)  # <- Wrapped method!

                msg = 'In 0.7.0, assertEqual() should raise DataError.'
                _self.assertTrue(isinstance(cm.exception, datatest.DataError), msg)

                diffs = list(cm.exception.differences)
                _self.assertEqual(diffs, [datatest.Missing(4)])

        error, failure = self._run_wrapped_test(_TestWrapper, 'test_method')
        self.assertIsNone(error)
        self.assertIsNone(failure)


class TestNormalizeReference(datatest.DataTestCase):
    def setUp(self):
        self.reference = MinimalSource([
            ('label1', 'value'),
            ('a', '65'),
            ('b', '70'),
        ])

        self.subject = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '17'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '5'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_normalize_set(self):
        original = set(['x', 'y', 'z'])
        normalized = self._normalize_required(original, 'distinct', 'label2')
        self.assertIs(original, normalized)  # Should return original unchanged.

    def test_alternate_reference_source(self):
        altsrc = MinimalSource([
            ('label1', 'value'),
            ('c', '75'),
            ('d', '80'),
        ])
        normalized = self._normalize_required(altsrc, 'distinct', 'label1')
        self.assertEqual(set(['c', 'd']), normalized)


class TestAssertSubjectColumns(datatest.DataTestCase):
    def setUp(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)

    def test_required_set(self):
        required_set = set(['label1', 'value'])
        self.assertSubjectColumns(required=required_set)  # <- test assert

    def test_required_source(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        required_source = MinimalSource(data)
        self.assertSubjectColumns(required=required_source)  # <- test assert

    def test_required_function(self):
        def lowercase(x):  # <- Helper function!!!
            return x == x.lower()
        self.assertSubjectColumns(required=lowercase)  # <- test assert

    def test_using_reference(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)
        self.reference = MinimalSource(data)
        self.assertSubjectColumns()  # <- test assert

    def test_extra(self):
        data = [('label1', 'label2', 'value'),
                ('a', 'x', '6'),
                ('b', 'y', '7')]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            required_set = set(['label1', 'value'])
            self.assertSubjectColumns(required=required_set)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Extra('label2')]))

    def test_missing(self):
        data = [('label1',),
                ('a',),
                ('b',)]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            required_set = set(['label1', 'value'])
            self.assertSubjectColumns(required=required_set)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Missing('value')]))

    def test_invalid(self):
        data = [('LABEL1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            def lowercase(x):  # <- Helper function!!!
                return x == x.lower()
            self.assertSubjectColumns(required=lowercase)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Invalid('LABEL1')]))


class TestNoDefaultSubject(datatest.DataTestCase):
    def test_no_subject(self):
        required = CompareSet([1,2,3])
        with self.assertRaisesRegex(NameError, "cannot find 'subject'"):
            self.assertSubjectSet(required)


class TestAssertSubjectSet(datatest.DataTestCase):
    def setUp(self):
        data = [('label1', 'label2'),
                ('a', 'x'),
                ('b', 'y'),
                ('c', 'z')]
        self.subject = MinimalSource(data)

    def test_collections(self):
        # Should all pass without error.
        required = set(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test set

        required = ['a', 'b', 'c']
        self.assertSubjectSet('label1', required)  # <- test list

        required = iter(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test iterator

        required = (x for x in ['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test generator

    def test_callable(self):
        # Should pass without error.
        required = lambda x: x in ['a', 'b', 'c']
        self.assertSubjectSet('label1', required)  # <- test callable

        # Multiple args. Should pass without error
        required = lambda x, y: x in ['a', 'b', 'c'] and y in ['x', 'y', 'z']
        self.assertSubjectSet(['label1', 'label2'], required)  # <- test callable

    def test_same(self):
        self.reference = self.subject
        self.assertSubjectSet('label1')  # <- test implicit reference

    def test_same_using_reference_from_argument(self):
        required = set(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test using arg

    def test_same_group_using_reference_from_argument(self):
        required = set([('a', 'x'), ('b', 'y'), ('c', 'z')])
        self.assertSubjectSet(['label1', 'label2'], required)  # <- test using arg

    def test_missing(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', '#'),  # <- Reference has one additional item.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet('label1')

        differences = cm.exception.differences
        self.assertEqual(differences, [Missing('d')])

    def test_extra(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            #('c', 'z'), <- Intentionally omitted.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet('label1')

        differences = cm.exception.differences
        self.assertEqual(differences, [Extra('c')])

    def test_invalid(self):
        with self.assertRaises(DataError) as cm:
            required = lambda x: x in ('a', 'b')
            self.assertSubjectSet('label1', required)

        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid('c')])

    def test_same_group(self):
        self.reference = self.subject
        self.assertSubjectSet(['label1', 'label2'])

    def test_missing_group(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', '#'),  # <- Reference has one additional item.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet(['label1', 'label2'])

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Missing(('d', '#'))])


class TestSubjectSum(datatest.DataTestCase):
    def setUp(self):
        self.src1_totals = MinimalSource([
            ('label1', 'value'),
            ('a', '65'),
            ('b', '70'),
        ])

        self.src1_records = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '17'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '5'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

        self.src2_records = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '18'),  # <- off by +1 (compared to src1)
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '4'),  # <- off by -1 (compared to src1)
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_passing_explicit_dict(self):
        self.subject = self.src1_records

        required = {'a': 65, 'b': 70}
        self.assertSubjectSum('value', ['label1'], required)

    def test_passing_explicit_callable(self):
        self.subject = self.src1_records

        required = lambda x: x in (65, 70)
        self.assertSubjectSum('value', ['label1'], required)

    def test_passing_implicit_reference(self):
        self.subject = self.src1_records
        self.reference = self.src1_totals

        self.assertSubjectSum('value', ['label1'])

    def test_failing_explicit_dict(self):
        self.subject = self.src2_records  # <- src1 != src2

        with self.assertRaises(DataError) as cm:
            required = {'a': 65, 'b': 70}
            self.assertSubjectSum('value', ['label1'], required)

        differences = cm.exception.differences
        expected = [Deviation(+1, 65, label1='a'),
                    Deviation(-1, 70, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))

    def test_failing_explicit_callable(self):
        self.subject = self.src2_records

        with self.assertRaises(DataError) as cm:
            required = lambda x: x in (65, 70)
            self.assertSubjectSum('value', ['label1'], required)

        differences = cm.exception.differences
        expected = [Invalid(Decimal(66), label1='a'),
                    Invalid(Decimal(69), label1='b')]
        #expected = [Invalid(66, label1='a'),
        #            Invalid(69, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))

    def test_failing_implicit_reference(self):
        self.subject = self.src2_records  # <- src1 != src2
        self.reference = self.src1_totals

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSum('value', ['label1'])

        differences = cm.exception.differences
        expected = [Deviation(+1, 65, label1='a'),
                    Deviation(-1, 70, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))


class TestAssertSubjectSumGroupsAndFilters(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2', 'label3', 'value'),
            ('a', 'x', 'foo', '18'),
            ('a', 'x', 'bar', '13'),
            ('a', 'y', 'foo', '11'),
            ('a', 'y', 'bar', '10'),
            ('a', 'z', 'foo',  '5'),
            ('a', 'z', 'bar', '10'),
            ('b', 'z', 'baz',  '4'),
            ('b', 'y', 'bar', '39'),
            ('b', 'x', 'foo', '25'),
        ])

        self.reference = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '18'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '4'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_group_and_filter(self):
        """Only groupby fields should appear in diff errors
        (kwds-filters should be omitted).
        """
        with self.assertRaises(DataError) as cm:
            self.assertSubjectSum('value', ['label1'], label2='y')

        differences = cm.exception.differences
        expected = [Deviation(+1, 20, label1='a'),
                    Deviation(-1, 40, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))


class TestAssertSubjectRegexAndNotDataRegex(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2'),
            ('0aaa', '001'),
            ('b9bb',   '2'),
            (' ccc', '003'),
        ])

    def test_regex_passing(self):
        self.assertSubjectRegex('label1', '\w\w')  # Should pass without error.

    def test_regex_failing(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectRegex('label2', '\d\d\d')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Invalid('2')])

    def test_regex_precompiled(self):
        regex = re.compile('[ABC]$', re.IGNORECASE)
        self.assertSubjectRegex('label1', regex)

    def test_not_regex_passing(self):
        self.assertSubjectNotRegex('label1', '\d\d\d')

    def test_not_regex_failing(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectNotRegex('label2', '^\d{1,2}$')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Invalid('2')])

    def test_not_regex_precompiled(self):
        regex = re.compile('^[ABC]')  # <- pre-compiled
        self.assertSubjectNotRegex('label1', regex)


class TestAssertSubjectUnique(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', 'z'),
            ('e', 'z'),
            ('f', 'z'),
        ])

    def test_single_column(self):
        self.assertSubjectUnique('label1')

    def test_multiple_columns(self):
        self.assertSubjectUnique(['label1', 'label2'])

    def test_duplicates(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectUnique('label2')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Extra('z')])


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
