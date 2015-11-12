# -*- coding: utf-8 -*-
from .case import DataTestCase
from .case import DataAssertionError

from .source import BaseSource
from .source import SqliteSource
from .source import CsvSource
from .source import MultiSource

from .extras import ExcelSource
from .extras import PandasSource

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .diff import NotProperSubset
from .diff import NotProperSuperset

from .sourceresult import ResultSet
from .sourceresult import ResultMapping

from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main


__version__ = '0.0.1a'

__all__ = [
    # Test case.
    'DataTestCase',
    'DataAssertionError',

    # Data sources.
    'BaseSource',
    'SqliteSource',
    'CsvSource',
    'MultiSource',
    'ExcelSource',
    'PandasSource',

    # Query results.
    'ResultSet',
    'ResultMapping',

    # Differences.
    'ExtraItem',
    'MissingItem',
    'InvalidItem',
    'InvalidNumber',

    # Test runner and command-line program.
    'DataTestRunner',
    'DataTestProgram',
    'main',
]
