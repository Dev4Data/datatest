# -*- coding: utf-8 -*-
from .case import DataTestCase

from .errors import ValidationErrors
from .errors import DataError
from .errors import Missing
from .errors import Extra
from .errors import Invalid
from .errors import Deviation

from .runner import mandatory
from .runner import skip
from .runner import skipIf
from .runner import skipUnless
from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main

from .dataaccess import DataSource
from .dataaccess import DataQuery
from .dataaccess import DataResult
from .dataaccess import working_directory


__version__ = '0.8.0.dev3'

__all__ = [
    # Test case.
    'DataTestCase',

    # Error classes.
    'ValidationErrors',
    'DataError',
    'Missing',
    'Extra',
    'Invalid',
    'Deviation',

    # Allowance context mangers.

    # Test runner and command-line program.
    'mandatory',
    'skip',
    'skipIf',
    'skipUnless',
    'DataTestRunner',
    'DataTestProgram',
    'main',

    # From Data Access sub-package.
    'DataSource',
    'DataQuery',
    'DataResult',
    'working_directory',
]

# Temporary alias for old "required" decorator.
required = mandatory
