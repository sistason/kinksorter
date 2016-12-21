#!/usr/bin/env python3

import unittest
from hamcrest import *
import os
import tempfile

from database import Database
from movie import Movie
from api import KinkAPI


class DatabaseShould(unittest.TestCase):

    def setUp(self):
        self.temp_database_file = tempfile.NamedTemporaryFile()
        self.temp_movie_file = tempfile.NamedTemporaryFile(suffix="12345")
        self.api = KinkAPI()
        self.database = Database(self.temp_database_file.name, self.api)

    def test_workflow(self):
        assert_that(self.database.movies, equal_to({}))

        m_ = Movie(self.temp_movie_file.name, self.api, {'foo': 'bar'})
        self.database.add_movie(m_)
        assert_that(self.database.movies, equal_to({self.temp_movie_file.name: m_}))

        self.database.write()
        assert_that(os.stat(self.temp_database_file.name).st_size, greater_than(10))

        database_instance_2 = Database(self.temp_database_file.name, self.api)
        database_instance_2.read()
        assert_that(database_instance_2.movies.get(self.temp_movie_file.name),
                    equal_to(self.database.movies.get(self.temp_movie_file.name)))

    def tearDown(self):
        self.temp_database_file.close()


if __name__ == "__main__":
    unittest.main()