#!/usr/bin/env python3

import logging
import os
import re
import shutil
import subprocess
import tqdm

from database import Database
from movie import Movie
import utils


class KinkSorter:
    SORTED_STORAGE_SUFFIX = '_kinksorted'
    LINKED_SORTED_STORAGE_SUFFIX = '_kinksorted_linked'
    UNSORTED_DIRECTORY_NAME = '#kinksorter_unsorted'

    def __init__(self, storage_root_path, settings_):
        self.storage_root_path = storage_root_path
        self._current_site_api = None
        self.settings = settings_
        Movie.settings = settings_

        self.database = Database(self.storage_root_path, self.settings)
        self.database.read()

    def update_database(self, merge_addresses):
        old_db_len_ = len(self.database.movies)
        self._scan_directory(self.storage_root_path, self.settings.RECURSION_DEPTH)
        new_own_movies_len_ = len(self.database.movies) - old_db_len_
        self._remove_deleted()
        self.database._own_movies = self.database.movies.copy()
        self.database.write()

        for merge_address in merge_addresses:
            self.scan_address(merge_address)

        new_db_len_ = len(self.database.movies)
        new_external_movies_len_ = new_db_len_ - new_own_movies_len_ - old_db_len_
        logging.info('{} movies found, {} new ones from our archive, {} new ones from other archives'.format(
            new_db_len_, new_own_movies_len_, new_external_movies_len_))

        untagged_movies = len([m_ for m_ in self.database.movies.values() if not m_])
        logging.info('{}/{} movies are untagged'.format(untagged_movies, new_db_len_))
        if untagged_movies > 50:
            logging.info('Many new movies found, downloading the whole API first')
            self.settings.apis_use_cache()

        try:
            self.update_all_movies()
        except (KeyboardInterrupt, EOFError):
            logging.info('Saving Database and exiting...')
            self.database.write()
            import sys
            sys.exit(0)
        except Exception as e:
            raise e

        self.database.write()

    def update_all_movies(self):
        log = logging.getLogger(__name__)
        log.addHandler(utils.TqdmLoggingHandler())
        for i, movie in enumerate(tqdm.tqdm(self.database.movies.values())):
            logging.debug(' ------------------------ '.format(movie.file_properties.base_name))
            logging.debug('"{}" - Working movie...'.format(movie.file_properties.print_base_name()))
            if not i % 10:
                self.database.write()

            if movie:
                logging.debug('Movie already completely tagged, skip.')
                continue

            logging.info('"{}" - Tagging movie...'.format(movie.file_properties.print_base_name()))
            movie.update_details()

    def _remove_deleted(self):
        if self.database.original:
            # Do not clean the original database, as that needs to be able to be reverted
            return

        movies_to_delete = [file_path for file_path in self.database.movies.keys() if not path.exists(file_path)]
        map(lambda f: self.database.del_movie(f), movies_to_delete)

    def scan_address(self, address):
        """ Add all movies at the address to the database """
        if re.match(r'ftps?://', address):
            pass
        elif re.match(r'https?://', address):
            pass
        else:
            self._scan_directory(address.replace('file://', ''), self.settings.RECURSION_DEPTH)

    def _scan_directory(self, dir_, recursion_depth=0, root_path=None):
        # TODO: make dictionary tree structure, to have every directory with an API.
        # (to be able to traverse in and out of directories, now previous API gets overwritten
        if root_path is None:
            root_path = dir_
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                logging.debug('\tScanning file {}...'.format(entry.path[:100]))
                if os.access(full_path, os.R_OK):
                    if self._is_video_file(full_path):
                        logging.debug('\tAdding movie {}...'.format(entry.path[:100]))
                        file_properties = utils.FileProperties(full_path, root_path)
                        m_ = Movie(file_properties, api=self._current_site_api)
                        self.database.add_movie(m_)
            if entry.is_dir():
                if recursion_depth == self.settings.RECURSION_DEPTH - 1 or \
                   os.path.dirname(full_path) == self.UNSORTED_DIRECTORY_NAME:
                    self._current_site_api = utils.get_correct_api(self.settings.apis, entry.name)
                    name_ = self._current_site_api.name if self._current_site_api else '<None>'
                    logging.info('Scanning site-directory (API: {}) {}...'.format(name_, entry.path))

                if recursion_depth > 0:
                    self._scan_directory(full_path, recursion_depth, root_path=root_path)

    @staticmethod
    def _is_video_file(full_path):
        mime_type = subprocess.check_output(['file', '-b', '--mime-type', full_path])
        if mime_type:
            mime_type = mime_type.decode('utf-8')
            if mime_type.startswith('video/') or mime_type.startswith('application/vnd.rn-realmedia'):
                return True
        return False

    def sort(self):
        logging.info('Sorting storage {}...'.format(self.storage_root_path))

        new_storage_path = self._build_new_storage_path()

        new_storage_database = Database(new_storage_path, self.settings)
        new_storage_database.original = False

        for old_movie_path, movie in self.database.movies.items():
            logging.debug('Sorting movie {}...'.format(old_movie_path))
            if not os.path.exists(old_movie_path):
                continue

            new_movie_path = self._build_new_movie_path(movie, new_storage_path)

            if not self._check_duplicate(movie, new_movie_path, old_movie_path):
                self._move_movie(old_movie_path, new_movie_path)
                self._cleanup_old_movie(old_movie_path)

                new_movie_file_properties = utils.FileProperties(new_movie_path, movie.file_properties.storage_root_path)
                new_movie = Movie(new_movie_file_properties, movie.api, scene_properties=movie.scene_properties)
                new_storage_database.add_movie(new_movie)

        new_storage_database.write()
        del new_storage_database

        self.database.print_merge_diff_list()

    def _build_new_storage_path(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        if self.settings.simulation and not old_storage_name.endswith(self.LINKED_SORTED_STORAGE_SUFFIX):
            suffix = self.LINKED_SORTED_STORAGE_SUFFIX
        elif not self.settings.simulation and self.storage_root_path.endswith(self.SORTED_STORAGE_SUFFIX):
            suffix = self.SORTED_STORAGE_SUFFIX
        else:
            suffix = ''

        new_storage_path = self.storage_root_path + suffix

        if not os.path.exists(new_storage_path):
            os.mkdir(new_storage_path)

        return new_storage_path

    def _check_duplicate(self, movie, new_movie_path, old_movie_path):
        if os.path.exists(new_movie_path):
            # Duplicate! Keep the one with bigger file size ;)
            old_movie_size_ = os.stat(new_movie_path).st_size
            new_movie_size_ = os.stat(movie.file_properties.file_path).st_size
            if old_movie_size_ > new_movie_size_:
                duplicates = [m.file_properties.file_path for m in self.database.get_movies(movie.scene_properties)
                              if m.file_properties.file_path != old_movie_path]
                logging.debug('"{}": "{}" is a duplicate of "{}", but is smaller and therefore skipped'.format(
                    movie, old_movie_path, duplicates))

                self._cleanup_old_movie(old_movie_path)
                return True
            else:
                os.remove(new_movie_path)

    def _build_new_movie_path(self, movie, new_storage_path):
        site_ = movie.scene_properties.site
        if not site_:
            site_ = os.path.join(self.UNSORTED_DIRECTORY_NAME, movie.file_properties.subdirectory_path)
        new_site_path = os.path.join(new_storage_path, site_)
        os.makedirs(new_site_path, exist_ok=True)
        new_movie_path = os.path.join(new_site_path, str(movie))
        return new_movie_path

    def _cleanup_old_movie(self, old_movie_path):
        if not self.settings.simulation and not re.match(r'https?://|ftps?://', old_movie_path):
            if os.path.exists(old_movie_path):
                os.remove(old_movie_path)
            if not os.listdir(os.path.dirname(old_movie_path)):
                os.removedirs(os.path.dirname(old_movie_path))

    def _move_movie(self, old_movie_path, new_movie_path):
        # realpath, to be able to sort linked directories.
        real_path = os.path.realpath(old_movie_path)
        if self.settings.simulation:
            if os.path.islink(old_movie_path):
                os.remove(old_movie_path)
            os.symlink(real_path, new_movie_path)
            self.database.add_to_merge_diff_list(real_path)
        else:
            if os.access(real_path, os.W_OK):
                shutil.move(real_path, new_movie_path)
            else:
                shutil.copy(real_path, new_movie_path)

    def revert(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        sorted_path = os.path.join(storage_path, old_storage_name + self.SORTED_STORAGE_SUFFIX)
        if not os.path.exists(sorted_path):
            logging.error('Cannot revert back "{}": "{}" not found!'.format(storage_path, sorted_path))
            return

        logging.info('Reverting storage "{}" back to "{}"...'.format(sorted_path, self.storage_root_path))

        n = len(self.database.movies)
        for i, (path_, movie) in enumerate(self.database.movies.items()):
            if os.path.exists(path_) and os.path.isfile(path_):
                continue
            if os.path.exists(path_):
                os.remove(path_)

            movie_name = str(movie)
            # TODO: subdirectories
            if movie.scene_properties.is_filled():
                site_ = movie.scene_properties.site
            else:
                site_ = os.path.join(self.UNSORTED_DIRECTORY_NAME, movie.file_properties.subdirectory_path)

            sorted_site_path = os.path.join(sorted_path, site_)
            sorted_movie_path = os.path.join(sorted_site_path, movie_name)
            if os.path.exists(sorted_movie_path):
                os.makedirs(os.path.dirname(path_), exist_ok=True)
                shutil.move(sorted_movie_path, path_)

                if not os.listdir(sorted_site_path):
                    os.rmdir(sorted_site_path)

            logging.debug('Reverted movie {}/{}:\n\t\t\t{} ->\n\t\t\t {}... '.format(i + 1, n, movie_name, path_))

        if not os.listdir(sorted_path):
            # Normally, the .kinksorter_db stays there, to not punch holes in the reversion.
            os.rmdir(sorted_path)

        logging.info('Finished reversion')


if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('%s is no directory or isn\'t writeable' % string)

    argparser = argparse.ArgumentParser(description="Easy Kink storage renaming/structuring")

    argparser.add_argument('storage_root_path', type=argcheck_dir,
                           help='Set the root path of the storage, has to be a writeable directory')
    argparser.add_argument('merge_addresses', nargs='*',
                           help='Merge given storage(s) into the root-storage.')
    argparser.add_argument('-t', '--tested', action="store_true",
                           help="Move movies instead of symlinking/listing them")
    argparser.add_argument('-i', '--interactive', action="store_true",
                           help="Confirm each action and query fails manually")
    argparser.add_argument('-r', '--revert', action="store_true",
                           help="Revert the sorted movies back to their original state in the database")
    argparser.add_argument('-s', '--shootid_template_dir', default=path.join(path.dirname(__file__), 'apis/templates'),
                           help="Set the template-directory for finding the Shoot ID")
    argparser.add_argument('-d', '--use_direct', action='store_true',
                           help="Query the sites directly instead of using the API")
    argparser.add_argument('-v', '--verbose', action='store_true',
                           help="Be more verbose")

    args = argparser.parse_args()

    settings = utils.Settings(vars(args))
    if args.verbose:
        logging.basicConfig(format='%(funcName)-23s: %(message)s',
                            level=logging.DEBUG)
        import pdb
        pdb.set_trace()
    else:
        logging.basicConfig(format='%(message)s',
                            level=logging.INFO)
    m = KinkSorter(args.storage_root_path, settings)

    if args.revert:
        m.revert()
    else:
        m.update_database(args.merge_addresses)
        m.sort()
