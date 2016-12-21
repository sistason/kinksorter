#!/usr/bin/env python3

import unittest
import socket
from hamcrest import *
from datetime import date

from api import KinkAPI


class KinkAPIShould(unittest.TestCase):

    def setUp(self):
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        except Exception:
            self.skipTest('No Internet')
        self.api = KinkAPI()

    def test_parsing(self):
        properties = self.api.query('id', "7675")
        assert_that(properties.get('title', ''),
                    equal_to('Holly Heart - Former collegiate athlete upside down, butt plugged, and made to cum!'))
        assert_that(properties.get('date', None),
                    equal_to(date(2009, 12, 17)))
        assert_that(properties.get('performers', []),
                    contains('Holly Heart'))
        assert_that(properties.get('site', ''),
                    equal_to('Device Bondage'))

suite = unittest.TestLoader().loadTestsFromTestCase(KinkAPIShould)

if __name__ == "__main__":
    unittest.main()