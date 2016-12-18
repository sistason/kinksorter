#!/usr/bin/env python3

import unittest
from hamcrest import *

from utils import *


class OmdbAPIShould(unittest.TestCase):

    def setUp(self):
        pass

    def test_query_id(self):
        assert_that(query_api('imdbID', "tt2306299").get('Title',''), equal_to('Vikings'))

if __name__ == "__main__":
    unittest.main()