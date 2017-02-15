#!/usr/bin/env python3

import tempfile
import unittest

from apis.kink_api import KinkAPI
from hamcrest import *
from movie import Movie
from utils import Settings, FileProperties, SceneProperties


class MovieShould(unittest.TestCase):

    def setUp(self):
        Movie.settings = Settings({})
        self.temp_movie_file = tempfile.NamedTemporaryFile()
        file_properties = FileProperties(self.temp_movie_file.name)
        scene_properties = {'shootid':12345}
        self.movie = Movie(file_properties, KinkAPI(), scene_properties=scene_properties)

    def test_recognize_kinkid(self):
        assert_that(self.movie.get_shootids_from_filename('12345'), contains(12345))
        assert_that(self.movie.get_shootids_from_filename('1999-12345-2007'), contains(12345))
        assert_that(self.movie.get_shootids_from_filename('2007'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('1080p'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('1080'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('(1080)'), contains(1080))
        assert_that(self.movie.get_shootids_from_filename('1080 720'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('1080 (720)'), contains(720))
        assert_that(self.movie.get_shootids_from_filename('12345 1234'), contains(12345, 1234))
        assert_that(self.movie.get_shootids_from_filename('2016-01-12'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('123456789'), equal_to([]))
        assert_that(self.movie.get_shootids_from_filename('091224'), equal_to([]))

    def test_logic_empty(self):
        assert_that(bool(self.movie), equal_to(False))
        assert_that(self.movie.scene_properties.is_empty(), equal_to(False))
        self.movie.scene_properties.set_shootid(0)
        assert_that(self.movie.scene_properties.is_empty(), equal_to(True))

    def test_logic_full(self):
        self.movie.scene_properties.set_title("test")
        self.movie.scene_properties.set_site("Test Site")
        self.movie.scene_properties.set_date(13371337)
        self.movie.scene_properties.set_performers(['Tester'])
        assert_that(bool(self.movie), equal_to(True))

    def test_name(self):
        assert_that(self.movie.get_shootids_from_filename("Waterbondage - 2006-04-21 3546 - Ava.wmv"), contains(3546))

    def tearDown(self):
        del self.movie

if __name__ == "__main__":
    unittest.main()
