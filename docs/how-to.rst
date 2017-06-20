
.. module:: datatest

.. meta::
    :description: How to work with reference data.
    :keywords: datatest, reference data


############
How-to Guide
############


************************
How to Assert Data Types
************************

.. code-block:: python

    class TypeTestCase(datatest.DataTestCase):
        def assertDataInstance(self, data, type, msg=None):
            """Assert that *data* elements are instances of *type*."""
            def check_type(x):
                return isinstance(x, type)
            msg = msg or 'must be instance of {0!r}'.format(type.__name__)
            self.assertValid(data, check_type, msg)

.. code-block:: python

    class TestTypes(TypeTestCase):
        def test_types(self):
            data = [-2, -1, 0, 1, 2]
            self.assertDataInstance(data, int)


******************************
How to Assert a Given Interval
******************************

.. code-block:: python

    class IntervalTestCase(datatest.DataTestCase):
        def assertInside(self, data, lower, upper, msg=None):
            """Assert that *data* elements fall inside given interval."""
            def interval(x):
                return lower <= x <= upper
            msg = msg or 'interval from {0!r} to {1!r}'.format(lower, upper)
            self.assertValid(data, interval, msg)

        def assertOutside(self, data, lower, upper, msg=None):
            """Assert that *data* elements fall outside given interval."""
            def not_interval(x):
                return not lower <= x <= upper
            msg = msg or 'interval from {0!r} to {1!r}'.format(lower, upper)
            self.assertValid(data, not_interval, msg)

.. code-block:: python

    class TestInterval(IntervalTestCase):
        def test_interval(self):
            data = [5, 7, 4, 5, 9]
            self.assertInside(data, lower=5, upper=10)


***************************
How to Assert an Inequality
***************************

.. code-block:: python

    class InequalityTestCase(datatest.DataTestCase):
        def assertDataGreater(self, data, requirement, msg=None):
            """Assert that *data* elements are greater than *requirement*."""
            def greater(x):
                return x > requirement
            msg = msg or 'must be greater than {0!r}'.format(requirement)
            self.assertValid(data, greater, msg)

        def assertDataLess(self, data, requirement, msg=None):
            """Assert that *data* elements are less than *requirement*."""
            def less(x):
                return x < requirement
            msg = msg or 'must be less than {0!r}'.format(requirement)
            self.assertValid(data, less, msg)

.. code-block:: python

    class TestGreaterThan(InequalityTestCase):
        def test_greater_than(self):
            data = [6, 7, 8, 9]
            self.assertDataGreater(data, 5)


**************************************
How to Check for Subsets and Supersets
**************************************

To assert subset or superset relations, use a :py:class:`set`
*requirement* together with the :meth:`allowedMissing()
<datatest.DataTestCase.allowedMissing>` or :meth:`allowedExtra()
<datatest.DataTestCase.allowedExtra>` context managers:

.. code-block:: python

    class MembershipTestCase(datatest.DataTestCase):
        def assertSubset(self, data, requirement, msg=None):
            """Assert that set of *data* is a subset of *requirement*."""
            with self.allowedMissing():
                self.assertValid(data, set(requirement), msg)

        def assertSuperset(self, data, requirement, msg=None):
            """Assert that set of *data* is a superset of *requirement*."""
            with self.allowedExtra():
                self.assertValid(data, set(requirement), msg)

.. code-block:: python

    class TestSubset(MembershipTestCase):
        def test_subset(self):
            data = {'a', 'b'}
            requirement = {'a', 'b', 'c', 'd'}
            self.assertSubset(data, requirement)


*************************
How to Use Reference Data
*************************

To compare two data sources that have the same field names,
we can create a single query and execute it twice (once for
each source). The pair of results can then be passed to
:meth:`assertValid() <datatest.DataTestCase.assertValid>`.

Below, we implement this with a helper-class ("ReferenceTestCase")
that has a single "assertReference()" method:

.. code-block:: python

    def setUpModule():
        global source_data, source_reference
        with datatest.working_directory(__file__):
            source_data = datatest.DataSource.from_csv('mydata.csv')
            source_reference = datatest.DataSource.from_csv('myreference.csv')


    class ReferenceTestCase(datatest.DataTestCase):
        def assertReference(self, select, **where):
            """
            assertReference(select, **where)
            assertReference(query)

            Asserts that the query results from the data under test
            match the query results from the reference data.
            """
            if isinstance(select, datatest.DataQuery):
                query = select
            else:
                query = datatest.DataQuery(select, **where)
            data = query(source_data)
            requirement = query(source_reference)
            self.assertValid(data, requirement)

Test-cases that inherit from this class can use "assertReference()":

.. code-block:: python

    class TestMyData(ReferenceTestCase):
        def test_select_syntax(self):
            self.assertReference({('A', 'B')}, B='foo')

        def test_query_syntax(self):
            query = datatest.DataQuery({'A': 'C'}).sum()
            self.assertReference(query)


***************************************
How to Allow Approximate String Matches
***************************************

.. code-block:: python

    class FuzzyTestCase(datatest.DataTestCase):
        def allowedFuzzyMatch(self, percent, msg=None):
            """Context manager to allow approximate string matches."""
            def fuzzy_match(a, b):  # Calculates Levenshtein/edit distance.
                maxlen = max(len(a), len(b))
                n, m = len(a), len(b)
                if n > m:
                    a, b = b, a
                    n, m = m, n
                current = range(n + 1)
                for i in range(1, m + 1):
                    previous, current = current, [i] + [0] * n
                    for j in range(1, n + 1):
                        add, delete = previous[j] + 1, current[j - 1] + 1
                        change = previous[j - 1]
                        if a[j - 1] != b[i - 1]:
                            change = change + 1
                        current[j] = min(add, delete, change)
                distance = current[n]
                similarity = 1 - (distance / maxlen)  # As percentage.
                return similarity >= percent

            return self.allowedArgs(fuzzy_match, msg)

.. code-block:: python

    class TestFuzzyMatch(FuzzyTestCase):
        def test_product_name(self):
            scraped_data = {
                'MKT-GA4530': '4 1/2 inch Angle Grinder',
                'FLK-87-5': 'Fluke 87-5 Multimeter',
                'LEW-K2698-1': 'Lincoln Elec Easy MIG 180',
            }
            catalog_reference = {
                'MKT-GA4530': '4-1/2in Angle Grinder',
                'FLK-87-5': 'Fluke 87-5 Multimeter',
                'LEW-K2698-1': 'Lincoln Easy MIG 180',
            }
            with self.allowedFuzzyMatch(percent=0.75):
                self.assertValid(scraped_data, catalog_reference)
