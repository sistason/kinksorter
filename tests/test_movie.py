#!/usr/bin/env python3

import unittest
from hamcrest import *
import tempfile

from movie import *


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

    def test_logic(self):
        self.movie.properties['id'] = 0
        assert_that(movie_is_empty(self.movie), equal_to(True))
        assert_that(movie_is_filled(self.movie), equal_to(False))
        assert_that(self.movie == self.movie, equal_to(True))


if __name__ == "__main__":
    unittest.main()