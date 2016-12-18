#!/usr/bin/env python3

import unittest
from hamcrest import *
import os
import tempfile

from database import Database
from movie import Movie


class DatabaseShould(unittest.TestCase):

    def setUp(self):
        self.temp_database_file = tempfile.NamedTemporaryFile()
        self.database = Database(self.temp_database_file.name)

    def test_0_initial(self):
        assert_that(self.database.movies, equal_to({}))

    def test_1_add_movie(self):
        m_ = Movie("/foo/12345.avi", {'foo':'bar'})
        self.database.add_movie(m_)
        assert_that(self.database.movies, equal_to({"/foo/12345.avi":m_}))

    def test_2_write_database(self):
        self.database.write_database()
        assert_that(os.stat(self.temp_database_file.name).st_size, greater_than(10))

    def test_3_reread_database(self):
        self.database_new = Database(self.temp_database_file.name)
        assert_that(self.database_new.movies, equal_to(self.database.movies))

    def tearDown(self):
        self.temp_database_file.close()


if __name__ == "__main__":
    unittest.main()