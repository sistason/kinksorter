#!/usr/bin/env python3

import unittest
from hamcrest import *
import tempfile

from movie import Movie


class MovieShould(unittest.TestCase):

    def setUp(self):
        self.temp_movie_file = tempfile.NamedTemporaryFile()
        self.movie = Movie(self.temp_movie_file.name, {}, {'id': "12345"})

    def test_properties_stay_unmodified(self):
        assert_that(self.movie.properties.get('id'), equal_to('12345'))

    def test_recognize_kinkid(self):
        assert_that(self.movie.get_kinkids('12345'), contains(12345))
        assert_that(self.movie.get_kinkids('1999-12345-2007'), contains(12345))
        assert_that(self.movie.get_kinkids('2007'), contains(2007))
        assert_that(self.movie.get_kinkids('1080p'), equal_to([]))
        assert_that(self.movie.get_kinkids('1080'), contains(1080))
        assert_that(self.movie.get_kinkids('1080 720'), contains(1080, 720))
        assert_that(self.movie.get_kinkids('12345 1234'), contains(12345, 1234))


if __name__ == "__main__":
    unittest.main()