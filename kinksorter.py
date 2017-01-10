#!/usr/bin/env python3

import logging
import os
import re
import shutil
import subprocess

from database import Database
from movie import Movie
import utils


class KinkSorter():

    def __init__(self, storage_root_path, settings):
        self.storage_root_path = storage_root_path
        self._current_site_api = settings.apis.get('Default', None)
        self.settings = settings
        Movie.settings = settings

        database_path = os.path.join(self.storage_root_path, '.kinksorter_db')
        self.database = Database(database_path, self.settings)
        self.database.read()

    def update_database(self, merge_addresses):
        self._scan_directory(self.storage_root_path, self.settings.RECURSION_DEPTH)
        self.database.own_movies = self.database.movies.copy()
        self.database.write()

        for merge_address in merge_addresses:
            self.scan_address(merge_address)

        new_db_len_ = len(self.database.movies)
        logging.info('{} movies found, {} new ones'.format(new_db_len_, new_db_len_-len(self.database.own_movies)))
        try:
            self.database.update_all_movies()
        except KeyboardInterrupt as e:
            logging.info('Saving Database and exiting...')
            self.database.write()

        self.database.write()

    def scan_address(self, address):
        """ Add all movies at the address to the database """
        if re.match(r'ftps?://', address):
            self._scan_ftp(address)
        elif re.match(r'https?://', address):
            self._scan_http(address)
        else:
            self._scan_directory(address.replace('file://', ''), self.settings.RECURSION_DEPTH)

    def _scan_ftp(self, address):
        listing = utils.get_ftp_listing(address)
        for path_, (name_, facts) in listing.items():
            full_path = os.path.join(path_, name_)
            # TODO
            #                self._current_site_api = utils.get_correct_api(self.settings.apis, path_)
            #                name_ = self._current_site_api.name if self._current_site_api else '<None>'
            #                logging.info('Scanning site-directory (API: {}) {}...'.format(name_, entry.path))

            #                if ("media-type" in facts and "video/" != facts["media-type"]
            #                    or "perm" in facts): # TODO: facts['perm'] == fitting

            #                    logging.debug('\tAdding movie {}...'.format(full_path))
            #                    m_ = Movie(full_path, api=self._current_site_api)
            #                    self.database.add_movie(m_)


            #                if recursion_depth > 0:
            #                    self._scan_directory(full_path, recursion_depth)

    def _scan_http(self, address):
            listing = utils.get_http_listing(address)
            for path_, (name_, facts) in listing.items():
                full_path = os.path.join(path_, name_)
                # TODO

    def _scan_directory(self, dir_, recursion_depth=0):
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                logging.debug('\tScanning file {}...'.format(entry.path))
                if os.access(full_path, os.R_OK):
                    mime_type = self._get_mime_type(full_path)
                    if mime_type and mime_type.decode('utf-8').startswith('video/'):
                        logging.debug('\tAdding movie {}...'.format(entry.path))
                        m_ = Movie(full_path, api=self._current_site_api)
                        self.database.add_movie(m_)
            if entry.is_dir():
                if recursion_depth == self.settings.RECURSION_DEPTH - 1:
                    self._current_site_api = utils.get_correct_api(self.settings.apis, entry.name)
                    name_ = self._current_site_api.name if self._current_site_api else '<None>'
                    logging.info('Scanning site-directory (API: {}) {}...'.format(name_, entry.path))

                if recursion_depth > 0:
                    self._scan_directory(full_path, recursion_depth)

    def _get_mime_type(self, full_path):
        return subprocess.check_output(['file', '-b', '--mime-type', full_path])

    def sort(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        new_storage_path = os.path.join(storage_path, old_storage_name + '_kinksorted')
        if self.settings.simulation:
            new_storage_path += '_0'
            while os.path.exists(new_storage_path):
                p_, cnt_ = new_storage_path.rsplit('_',1)
                new_storage_path = p_ + '_' + str(int(cnt_)+1) if cnt_.isdigit() else p_ + '_0'

        if not os.path.exists(new_storage_path):
            os.mkdir(new_storage_path)

        new_storage_database = Database(os.path.join(new_storage_path, ".kinksorter_db"), self.settings)

        for old_movie_path, movie in self.database.movies.items():
            if not (os.path.exists(old_movie_path) or os.access(old_movie_path, os.R_OK)):
                continue
            site_ = movie.properties['site'] if 'site' in movie.properties and movie.properties['site'] else 'unsorted'
            new_site_path = os.path.join(new_storage_path, site_)
            if not os.path.exists(new_site_path):
                os.mkdir(new_site_path)

            new_movie_path = os.path.join(new_site_path, str(movie))

            if os.path.exists(new_movie_path):
                # Duplicate! Keep the one with bigger file size ;)
                old_movie_size_ = os.stat(new_movie_path).st_size
                new_movie_size_ = os.stat(movie.file_path).st_size
                if old_movie_size_ >= new_movie_size_:
                    logging.debug('"{}" was duplicate of "{}", but was smaller and is therefore skipped'.format(
                        movie, new_movie_path))
                    continue
                os.remove(new_movie_path)

            self._move_movie(old_movie_path, new_movie_path)

            new_movie = Movie(new_movie_path, None, properties=movie.properties)
            new_storage_database.add_movie(new_movie)

        new_storage_database.write()
        del new_storage_database

        if self.database.merge_diff_list:
            print('Files to get:')
            print('\t'+'\n\t'.join(self.database.merge_diff_list))

    def _move_movie(self, old_movie_path, new_movie_path):
        if re.match(r'https?://|ftps?://', old_movie_path):
            if self.settings.simulation:
                self.database.add_to_merge_diff_list(old_movie_path)
            else:
                file_ = utils.get_remote_file(old_movie_path)
                if file_ is not None and os.path.exists(file_):
                    shutil.move(file_, new_movie_path)
        else:
            if self.settings.simulation:
                os.symlink(old_movie_path, new_movie_path)
                self.database.add_to_merge_diff_list(old_movie_path)
            else:
                shutil.move(old_movie_path, new_movie_path)

    def revert(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        sorted_path = os.path.join(storage_path, old_storage_name + '_kinksorted')

        n = len(self.database.movies)
        for i, (path_, movie) in enumerate(self.database.movies.items()):
            if os.path.exists(path_):
                continue
            movie_name = str(movie)
            site_ = movie.properties['site'] if 'site' in movie.properties and movie.properties['site'] else 'unsorted'
            sorted_site_path = os.path.join(sorted_path, site_)
            sorted_movie_path = os.path.join(sorted_site_path, movie_name)
            if os.path.exists(sorted_movie_path):
                if re.match(r'https?://|ftps?://', path_):
                    logging.info('Movie "{}" came from read-only storage'.format(movie_name))
                    new_ro_dir = os.path.join(storage_path, 'from_read-only')
                    if not os.path.exists(new_ro_dir):
                        os.mkdir(new_ro_dir)
                    new_ro_site_dir = os.path.join(new_ro_dir, site_)
                    if not os.path.exists(new_ro_site_dir):
                        os.mkdir(new_ro_site_dir)
                    shutil.move(sorted_movie_path, os.path.join(new_ro_site_dir, movie_name))
                else:
                    shutil.move(sorted_movie_path, path_)

                if not os.listdir(sorted_site_path):
                    os.rmdir(sorted_site_path)

            logging.info('Reverted movie "{}"... ({}/{})'.format(movie_name, i + 1, n))

        if not os.listdir(sorted_path):
            os.rmdir(sorted_path)


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
    argparser.add_argument('-s', '--shootid_template', default='templates/shootid.jpeg',
                           help="Set the template-image for finding the Shoot ID")

    args = argparser.parse_args()

    settings = utils.Settings(vars(args))
    m = KinkSorter(args.storage_root_path, settings)

    logging.basicConfig(format='%(funcName)s: %(message)s',
                        level=logging.INFO)
    if args.revert:
        m.revert()
    else:
        m.update_database(args.merge_addresses)
        m.sort()
