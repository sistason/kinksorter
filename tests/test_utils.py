#!/usr/bin/env python3

import unittest
from datetime import date

import utils
from hamcrest import *


class FilePropertiesShould(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty(self):
        file_properties = utils.FileProperties('')
        assert_that(file_properties.base_name, equal_to(''))
        assert_that(file_properties.file_path, equal_to(''))
        assert_that(file_properties.extension, equal_to(''))
        assert_that(file_properties.storage_root_path, equal_to('/'))
        assert_that(file_properties.relative_path, equal_to(''))
        assert_that(file_properties.subdirectory_path, equal_to(''))

    def test_full(self):
        file_properties = utils.FileProperties('/tmp/foo/baz/bazinga/movie1337.mp4', storage_root_path='/tmp/foo')
        assert_that(file_properties.base_name, equal_to('movie1337'))
        assert_that(file_properties.file_path, equal_to('/tmp/foo/baz/bazinga/movie1337.mp4'))
        assert_that(file_properties.extension, equal_to('.mp4'))
        assert_that(file_properties.storage_root_path, equal_to('/tmp/foo'))
        assert_that(file_properties.relative_path, equal_to('baz/bazinga/movie1337.mp4'))
        assert_that(file_properties.subdirectory_path, equal_to('baz/bazinga'))

    def test_no_storage_root_path(self):
        file_properties = utils.FileProperties('/tmp/foo/baz/bazinga/movie1337.mp4')
        assert_that(file_properties.storage_root_path, equal_to('/'))
        assert_that(file_properties.relative_path, equal_to('tmp/foo/baz/bazinga/movie1337.mp4'))
        assert_that(file_properties.subdirectory_path, equal_to('tmp/foo/baz/bazinga'))


class ScenePropertiesShould(unittest.TestCase):
    def setUp(self):
        pass

    def test_(self):
        pass

if __name__ == "__main__":
    unittest.main()
