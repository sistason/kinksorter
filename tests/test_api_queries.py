#!/usr/bin/env python3

import unittest
import socket
from hamcrest import *

from utils import *


class OmdbAPIShould(unittest.TestCase):

    def setUp(self):
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            self.has_internet_connection = True
        except Exception:
            self.has_internet_connection = False

    def test_query_id(self):
        if not self.has_internet_connection:
            self.skipTest('No Internet')
        assert_that(query_api('id', "12345").get('TODO',''), equal_to('TODO'))

    def test_query_date(self):
        if not self.has_internet_connection:
            self.skipTest('No Internet')
        assert_that(query_api('date', "2016-12-12").get('TODO',''), equal_to('TODO'))

    def test_query_name(self):
        if not self.has_internet_connection:
            self.skipTest('No Internet')
        assert_that(query_api('name', "").get('TODO', ''), equal_to('TODO'))


if __name__ == "__main__":
    unittest.main()