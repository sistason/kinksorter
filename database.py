import logging
import json
import tqdm
import datetime

from collections import OrderedDict
from os import path, access, W_OK, R_OK

from movie import Movie


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class Database:

    def __init__(self, database_path, settings):
        self._path = database_path
        self._settings = settings
        self.movies = {}  # filename:Movie(),
        self.own_movies = {}
        self.merge_diff_list = {}

    def add_movie(self, movie):
        if not self.check_movie_duplicates(movie):
            self.movies[movie.file_path] = movie

    def check_movie_duplicates(self, movie):
        """ Checks for duplicate files, not duplicate movies. """
        for m_ in self.movies.keys():
            if movie.file_path == m_:
                logging.debug('Movie "{}" was already in the database'.format(movie))
                return True

    def add_to_merge_diff_list(self, movie_path):
        if movie_path not in self.merge_diff_list and movie_path not in self.own_movies.keys():
            self.merge_diff_list.append(movie_path)

    def update_all_movies(self):
        log = logging.getLogger(__name__)
        log.addHandler(TqdmLoggingHandler())
        for i, movie in enumerate(tqdm.tqdm(self.movies.values())):
            if movie:
                continue

            logging.info('Fetching details for movie "{}"...'.format(movie.base_name))
            movie.update_details()

            if not i % 10:
                self.write()

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

            Movie.settings = self._settings
            _movies = OrderedDict()
            for file_path, properties in _decoded.items():
                # Date was not json serializable, format from timestamp
                properties['date'] = datetime.date.fromtimestamp(int(properties.get('date',0)))
                api = self._settings.apis.get(properties.pop('api',None), None)
                m_ = Movie(file_path, api, properties=properties)
                _movies[file_path] = m_

        except Exception as e:
            logging.error("Database '{}' possibly corrupted (Error: '{}'), recreating!".format(self._path, e))
            return
        self.movies = _movies

    def write(self):
        _database = {}
        for m_ in self.movies.values():
            _properties = m_.properties.copy()
            # Date is not json serializable, format to timestamp
            _properties['date'] = _properties['date'].strftime('%s') if 'date' in _properties else 0
            _properties['api'] = m_.api.name if m_.api is not None else None
            _database[m_.file_path] = _properties

        _encoded = json.dumps(_database)
        with open(self._path, 'w') as f:
            f.write(_encoded)
