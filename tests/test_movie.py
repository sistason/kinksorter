#!/usr/bin/env python3

import unittest
from hamcrest import *
import socket

from movie import Movie


class MovieShould(unittest.TestCase):

    def setUp(self):
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            self.has_internet_connection = True
        except Exception:
            self.has_internet_connection = False

    def test_properties_stay_unmodified(self):
        vikings = Movie('', {'imdbID': "tt2306299"})
        assert_that(vikings.properties.get('imdbID'), equal_to('tt2306299'))

    def test_recognize_imdbID(self):
        if not self.has_internet_connection:
            self.skipTest('No Internet')
        vikings = Movie("/tt2306299.avi")
        assert_that(vikings.properties.get('imdbID'), equal_to('tt2306299'))

if __name__ == "__main__":
    unittest.main()