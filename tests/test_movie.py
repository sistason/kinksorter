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
        m_ = Movie('', {'id': "12345"})
        assert_that(m_.properties.get('id'), equal_to('12345'))

    def test_recognize_kinkid(self):
        if not self.has_internet_connection:
            self.skipTest('No Internet')
        m_ = Movie("/12345.avi")
        assert_that(m_.properties.get('id'), equal_to('12345'))

if __name__ == "__main__":
    unittest.main()