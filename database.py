import logging
import datetime

from collections import OrderedDict
from os import path, access, W_OK, R_OK

from utils import *
from movie import Movie


class Database():
    _path = ''
    movies = {} # filename:Movie(),

    def __init__(self, database_path):
        self._path = database_path
        self._read_database()

    def add_movie(self, movie):
        # TODO: check duplicate
        self.movies[movie.file_path] = movie

    def _read_database(self):
        if not path.exists(self._path):
            logging.info("No database found at '{}', recreating!".format(self._path))
            return

        if not access(self._path, W_OK):
            logging.error("No write-permissions for database '{}'!".format(self._path))
            return
        if not access(self._path, R_OK):
            logging.error("No read-permissions for database '{}'!".format(self._path))
            return

        try:
            with open(self._path, 'r') as f:
                _data = f.read()

            if not _data:
                logging.info("Database at '{}' was empty, recreating!".format(self._path))
                return

            _decoded = json.loads(_data)

            current_time = datetime.datetime.now()
            _movies = OrderedDict()
            for file_path, properties in _decoded:
                if not (path.exists(file_path) and access(file_path, R_OK)):
                    continue

                m_ = Movie(file_path, properties['properties'])
                _movies[file_path] = m_

        except Exception as e:
            logging.error("Database '{}' possibly corrupted (Error: '{}'), recreating!".format(self._path, e))
            return
        self.movies = _movies

    def write_database(self):
        _database = {m_.file_path: {'properties': m_.properties} for m_ in self.movies.values()}
        _encoded = json.dumps(_database)
        with open(self._path, 'w') as f:
            f.write(_encoded)
