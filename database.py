import logging
import datetime

from collections import OrderedDict
from os import path, access, W_OK, R_OK

from api import *
from movie import Movie


class Database():
    _path = ''
    movies = {} # filename:Movie(),

    def __init__(self, database_path, api):
        self._path = database_path
        self._api = api

    def add_movie(self, movie):
        # TODO: check duplicate
        self.movies[movie.file_path] = movie

    def read(self):
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

            _movies = OrderedDict()
            for file_path, properties in _decoded.items():
                if not (path.exists(file_path) and access(file_path, R_OK)):
                    continue

                # Date was not json serializable, format from timestamp
                properties['date'] = datetime.date.fromtimestamp(int(properties.get('date',0)))
                m_ = Movie(file_path, self._api, properties)
                _movies[file_path] = m_

        except Exception as e:
            logging.error("Database '{}' possibly corrupted (Error: '{}'), recreating!".format(self._path, e))
            return
        self.movies = _movies

    def write(self):
        _database = {}
        for m_ in self.movies.values():
            _properties = m_.properties
            # Date is not json serializable, format to timestamp
            _properties['date'] = _properties['date'].strftime('%s') if 'date' in _properties else 0
            _database[m_.file_path] = _properties

        _encoded = json.dumps(_database)
        with open(self._path, 'w') as f:
            f.write(_encoded)
