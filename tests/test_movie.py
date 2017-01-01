#!/usr/bin/env python3

import unittest
from hamcrest import *
import tempfile

from movie import Movie, movie_is_empty, movie_is_filled
from api import KinkAPI
from kinksorter import Settings

class MovieShould(unittest.TestCase):

    def setUp(self):
        Movie.settings = Settings({})
        self.temp_movie_file = tempfile.NamedTemporaryFile()
        self.movie = Movie(self.temp_movie_file.name, KinkAPI(), {'id': "12345"})

    def test_properties_stay_unmodified(self):
        assert_that(self.movie.properties.get('id'), equal_to('12345'))

    def test_recognize_kinkid(self):
        assert_that(self.movie.get_shootids('12345'), contains(12345))
        assert_that(self.movie.get_shootids('1999-12345-2007'), contains(12345))
        assert_that(self.movie.get_shootids('2007'), equal_to([]))
        assert_that(self.movie.get_shootids('1080p'), equal_to([]))
        assert_that(self.movie.get_shootids('1080'), contains(1080))
        assert_that(self.movie.get_shootids('1080 720'), contains(1080, 720))
        assert_that(self.movie.get_shootids('12345 1234'), contains(12345, 1234))
        assert_that(self.movie.get_shootids('2016-01-12'), equal_to([]))
        assert_that(self.movie.get_shootids('123456789'), equal_to([]))

    def test_logic(self):
        self.movie.properties['id'] = 0
        assert_that(movie_is_empty(self.movie), equal_to(True))
        assert_that(movie_is_filled(self.movie), equal_to(False))
        assert_that(self.movie == self.movie, equal_to(True))


if __name__ == "__main__":
    unittest.main()