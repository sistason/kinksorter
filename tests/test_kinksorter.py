#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock
from hamcrest import *
import os
import shutil
import tempfile
import datetime
import logging

from movie import Movie
from utils import Settings
from kinksorter import KinkSorter


class KinksorterShould(unittest.TestCase):

    def setUp(self):
        self.root_storage = tempfile.TemporaryDirectory()
        settings = Settings({'tested':True})
        settings.apis['Kink.com']._site_capabilities = []
        if settings.apis.get('Default', None) is not None:
            settings.apis['Default']._site_capabilities = []
        self.kinksorter = KinkSorter(self.root_storage.name, settings)
        self.kinksorter._get_mime_type = MagicMock(return_value=b"video/")

        self.file1 = tempfile.NamedTemporaryFile(dir=self.root_storage.name, delete=False)
        self.file2 = tempfile.NamedTemporaryFile(dir=self.root_storage.name, delete=False)
        self.dir3 = tempfile.TemporaryDirectory(dir=self.root_storage.name)
        self.file3 = tempfile.NamedTemporaryFile(dir=self.dir3.name, delete=False)

    def test_scan(self):
        # print(len(self.kinksorter.database.movies))
        # TODO: understand why unittest does only one setup, but claims to do all seperate
        self.kinksorter.scan_address(self.kinksorter.storage_root_path)
        assert_that(len(self.kinksorter.database.movies), equal_to(3))

    def test_sort(self):
        properties_ = {'title': 'test', 'performers': ['Testy Mc. Test'],
                       'date': datetime.date(2007, 1, 1), 'site': 'Test Site', 'id': 1337}
        properties1 = properties_.copy()
        properties1['title'] = "test1"
        properties2 = properties_.copy()
        properties2['title'] = "test2"
        properties3 = properties_.copy()
        properties3['site'] = ""

        self.m1 = Movie(self.file1.name, None, properties1)
        self.m2 = Movie(self.file2.name, None, properties2)
        self.m3 = Movie(self.file3.name, None, properties3)

        assert_that(len(os.listdir(self.kinksorter.storage_root_path)), equal_to(3))
        self.kinksorter.database.add_movie(self.m1)
        self.kinksorter.database.add_movie(self.m2)
        self.kinksorter.database.add_movie(self.m3)
        self.kinksorter.sort()
        sorted_path = self.kinksorter.storage_root_path+'_kinksorted'
        assert_that(os.path.exists(sorted_path))
        assert_that(os.path.exists(os.path.join(sorted_path, 'Test Site')))
        assert_that(os.path.exists(os.path.join(sorted_path, 'unsorted')))
        assert_that(len(os.listdir(os.path.join(sorted_path, 'Test Site'))), equal_to(2))
        assert_that(len(os.listdir(self.kinksorter.storage_root_path)), equal_to(1))

    def test_revert(self):
        self.test_sort()
        self.kinksorter.revert()

        sorted_path = self.kinksorter.storage_root_path + '_kinksorted'
        assert_that(len(os.listdir(self.kinksorter.storage_root_path)), equal_to(3))
        assert_that(not os.path.exists(os.path.join(sorted_path, 'Test Site')))

    def tearDown(self):
        self.file3.delete = True
        self.file3.close()
        self.dir3.cleanup()
        self.file2.delete = True
        self.file2.close()
        self.file1.delete = True
        self.file1.close()
        self.root_storage.cleanup()
        if os.path.exists(self.kinksorter.database._path):
            os.remove(self.kinksorter.database._path)
        sorted_path = self.kinksorter.storage_root_path + '_kinksorted'
        if os.path.exists(sorted_path):
            shutil.rmtree(sorted_path)


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                        level=logging.WARNING)
    unittest.main()