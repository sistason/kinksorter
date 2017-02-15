import logging
import json

from collections import OrderedDict
from os import path, access, W_OK, R_OK

from movie import Movie
import utils


class Database:

    def __init__(self, database_dir, settings):
        database_path = path.join(database_dir, '.kinksorter_db')
        self._path = database_path
        self._settings = settings
        self.movies = {}  # filename:Movie(),
        self._own_movies = {}
        self.merge_diff_list = []
        self.original = True

    def add_movie(self, movie):
        """ Add the movie to the database, if it is not already in there. """
        if not self.check_movie_duplicates(movie):
            self.movies[movie.file_properties.file_path] = movie

    def del_movie(self, movie_path):
        """ Remove the movie from the database """
        item = self.movies.pop(movie_path, None)
        del item

    def get_movies(self, scene_properties):
        """ Get all movies matching the scene properties """
        movies = []
        for movie in self.movies.values():
            if movie.scene_properties == scene_properties:
                movies.append(movie)
        return movies

    def check_movie_duplicates(self, movie):
        """ Checks for duplicate files, not duplicate movies. """
        for m_ in self.movies.keys():
            if movie.file_properties.file_path == m_:
                logging.debug('Movie "{}" was already in the database'.format(m_))
                return True

    def add_to_merge_diff_list(self, movie_path):
        """ Add external movies to the diff-list, if they are no duplicates and external """
        if movie_path not in self.merge_diff_list and movie_path not in self._own_movies.keys():
            self.merge_diff_list.append(movie_path)

    def print_merge_diff_list(self):
        """ Outputs the diff-list """
        if not self.merge_diff_list:
            return

        print('Files to get:')
        print('\t' + '\n\t'.join(self.merge_diff_list))

    def read(self):
        """ Read in/Create the database from file"""
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
            self.original = _decoded.pop('original', False)

            Movie.settings = self._settings
            _movies = OrderedDict()
            for file_path, serialized in _decoded.items():
                api = self._settings.apis.get(serialized.pop('api', None), None)
                file_properties = utils.FileProperties(**serialized.pop('file_properties', {}))
                scene_properties = utils.SceneProperties(**serialized.get('scene_properties',{}))

                m_ = Movie(file_properties, api, scene_properties=scene_properties)
                _movies[file_path] = m_

        except Exception as e:
            logging.error("Database '{}' possibly corrupted (Error: '{}'), recreating!".format(self._path, e))
            return
        self.movies = _movies

    def write(self):
        """ Write the database to file """
        dict_to_write = {k_: m_.serialize() for k_, m_ in self.movies.items()}
        dict_to_write['original'] = self.original
        _encoded = json.dumps(dict_to_write)
        with open(self._path, 'w') as f:
            f.write(_encoded)
