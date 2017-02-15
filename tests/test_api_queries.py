#!/usr/bin/env python3

import socket
import unittest
from datetime import date

from apis.kink_api import KinkAPI
from hamcrest import *


class KinkAPIShould(unittest.TestCase):

    def setUp(self):
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        except Exception:
            self.skipTest('No Internet')
        self.api = KinkAPI()

    def test_direct_parsing(self):
        properties = self.api.query_direct_shoot_id(7675)
        self._validate(properties)

    def test_api_parsing(self):
        properties = self.api.query_api('shoots', 'shootid', 7675)
        self._validate(properties)

    def test_cache_parsing(self):
        import time
        self.api.use_cache()
        while self.api._cache_updating:
            time.sleep(1)

        properties = self.api.query_cache('shoots', 'shootid', 7675)
        print(properties)
        self._validate(properties)

    def test_date_parsing(self):
        date_ = date(2009, 12, 17)
        properties = self.api.query_api('shoots', 'date', date_.strftime('%Y-%m-%d'))
        assert_that(len(properties), equal_to(2))
        properties = [p for p in properties if p.get('shootid', 0) == 7675]
        self._validate(properties)

    def test_name_parsing(self):
        properties = self.api.query_api('shoots', 'title', "Former collegiate athlete upside down")
        self._validate(properties)

    @staticmethod
    def _validate(properties_):
        assert_that(len(properties_), equal_to(1))
        properties = properties_[0]
        assert_that(properties.get('shootid', 0),
                    equal_to(7675))
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
