
.. module:: datatest

.. meta::
    :description: How to control difference objects.
    :keywords: datatest, differences


###################################
How to Control "Difference" Objects
###################################

When using a predicate function (see :ref:`predicate-docs`),
datatest will generate a "difference" object each time the
function returns ``False``. By default, an :class:`Invalid`
instance is generated but it's possible to customize this
behavior.

When a predicate function returns a difference---instead of
``False``---the returned difference is used in place of an
automatically generated one (see :ref:`difference-docs`).

Below, the predicate function ``max100()`` returns ``True``
when values are less than or equal to 100 but it returns a
:class:`Deviation` when values are greater than 100 (instead
of returning ``False``):

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate
            from datatest import Deviation


            def test_max_value():

                data = [98, 99, 100, 101, 102]

                def max100(x):  # <- Helper (predicate function).
                    return x <= 100 or Deviation(x - 100, 100)

                validate(data, max100)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase
            from datatest import Deviation


            class MyTest(DataTestCase):

                def test_max_value(self):

                    data = [98, 99, 100, 101, 102]

                    def max100(x):  # <- Helper (predicate function).
                        return x <= 100 or Deviation(x - 100, 100)

                    self.assertValid(data, max100)

