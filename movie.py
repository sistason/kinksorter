import re
import logging
import datetime
import os


class Movie:
    UNLIKELY_NUMBERS = {'quality': [360, 480, 720, 1080, 1440, 2160],
                        'date': list(range(1999, 2030))+list(range(0, 32))}
    settings = None

    def __init__(self, file_path, api, properties=None):
        self.file_path = file_path
        self._unlikely_shootid_quality_re = re.compile('|'.join(str(i) + 'p' for i in self.UNLIKELY_NUMBERS['quality']))
        # Filter out dates like 091224 or (20)150101
        self._unlikely_shootid_date_re = re.compile('([01]\d)({})({})'.format(
            '|'.join(['{:02}'.format(i) for i in range(1, 13)]),
            '|'.join(['{:02}'.format(i) for i in range(1, 32)])
        ))
        self.api = api

        base_path_, filename_ = os.path.split(file_path)
        _, self.subdirname = os.path.split(base_path_)
        self.base_name, self.extension = os.path.splitext(filename_)

        if properties is None:
            properties = {}
        self.properties = {'title': '', 'performers': [], 'date': datetime.date(1970, 1, 1), 'site': '', 'id': 0}
        self.properties.update(properties)

        if self.settings is None:
            logging.warning('Settings were not set by calling class! This will break!')

    def update_details(self):
        if self.api is None:
            return
        shootids = self.get_shootids(self.base_name)
        if shootids:
            if len(shootids) > 1:
                shootid = self.interactive_choose_shootid(shootids)
            else:
                shootid = shootids[0]
        else:
            shootid = self.api.get_shootid_through_image_recognition(self.file_path)

        if shootid:
            result = self.api.query_for_id(shootid)
            if self.interactive_confirm(result):
                self.properties.update(result)
        else:
            t_ = re.search(r"\d{4}\W\d{1,2}\W\d{1,2}", self.base_name)
            likely_date = t_.group(0) if t_ else ''
            self.properties.update(self.interactive_query(likely_date))

    def get_shootids(self, base_name):
        base_name = re.sub(self._unlikely_shootid_quality_re, '', base_name)
        search_shootid = []

        # FIXME: \d{2,6} scrambles numbers, (?:\D|^)(\d{2,6})(?:\D|$) has problems
        for k in re.findall(r"\d+", base_name):
            if 2 <= len(k) <= 6 and int(k) not in self.UNLIKELY_NUMBERS['date']:
                if self._unlikely_shootid_date_re.search(k):
                    logging.debug('"{}": Most likely no shootid, but a date. Skipping...'.format(k))
                    continue
                search_shootid.append(int(k))

        if len(search_shootid) > 1:
            logging.info('Multiple Shoot IDs found, choose one')
        return search_shootid

    def interactive_query(self, likely_date=''):
        if not self.settings.interactive:
            return {}

        print('Unable to find anything to work automatically. Please help with input')
        print('Movie in Question:', self.file_path, 'Likely date:', likely_date)

        user_input = "don't stop yet :)"
        while user_input:
            user_input = input('Please input an ID, a data or a name of the movie in the format:\n  ' +
                               'ID: i<id>; Date: d<date YYYY-mm-dd>; Name: <name>; Abort: <empty string>\n   ').strip()
            if user_input.startswith('i'):
                id_ = int(user_input[1:]) if user_input[1:].isdigit() else 0
                if not id_:
                    print('"{}" was no number, please repeat!'.format(user_input[1:]))
                    continue
                result = self.api.query_for_id(id_)
                if self.interactive_confirm(result):
                    return result
            elif user_input.startswith('d'):
                date_string = user_input[1:]
                try:
                    date_ = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
                    print('Date interpreted as {}'.format(date_))
                except (ValueError, AttributeError):
                    print('Could not parse date "{}".'.format(date_string))
                    continue

                print('Sadly, no API is yet available to search for a date :(')
                continue
            elif user_input:
                name_ = user_input
                print('Sadly, no API is yet available to search for a name :(')
                continue
            else:
                print('Leaving movie "{}" untagged.'.format(self.base_name))
                continue

        return {}

    def interactive_confirm(self, result):
        logging.info('\told: {}{}'.format(self.base_name, self.extension))
        logging.info('\tnew: {}'.format(format_properties(result)))
        answer = input('Is this okay? Y, n?') if self.settings.interactive else 'Y'
        return True if not answer or answer.lower().startswith('y') else False

    def interactive_choose_shootid(self, likely_ids):
        if not self.settings.interactive:
            return max(likely_ids)

        id_ = None
        while not id_ or not id_.isdigit():
            try:
                id_ = input('Choose the Shoot ID of file "{}". Likely are:\n\t{}'.format(
                                        self.file_path, '\n\t'.join(map(str, likely_ids))))
            except KeyboardInterrupt:
                return 0
        return int(id_)

    def __eq__(self, other):
        if movie_is_empty(self) and movie_is_empty(other):
            return self.base_name == other.base_name
        return self.file_path == other.file_path or \
            (self.properties.get('title', '') == other.properties.get('title', '')
                and self.properties.get('performers', []) == other.properties.get('performers', [])
                and self.properties.get('date', None) == other.properties.get('date', None)
                and self.properties.get('site', '') == other.properties.get('site', '')
                and self.properties.get('id', 0) == other.properties.get('id', 0))

    def __str__(self):
        return format_movie(self)

    def __bool__(self):
        return movie_is_filled(self)


def format_movie(movie):
    if movie_is_empty(movie):
        return '<untagged> | {}_{}{}'.format(movie.subdirname, movie.base_name, movie.extension)
    ret = ''
    if not movie_is_filled(movie):
        ret = movie.base_name + ' <incomplete_tagged> | '

    ret += '{site} - {date} - {title} [{perfs}] ({id}){ext}'.format(
        site=movie.properties.get('site', '').replace(' ', ''),
        date=movie.properties.get('date', ''),
        title=movie.properties.get('title', ''),
        perfs=', '.join(movie.properties.get('performers', '')),
        id=movie.properties.get('id', ''),
        ext=movie.extension)
    return ret


class Fake:
    def __init__(self, p, b=''):
        self.properties = p
        self.base_name = b
        self.subdirname = 'fake'
        self.extension = ''


def format_properties(properties):
    return format_movie(Fake(properties))


def movie_is_filled(movie):
    return bool(movie.properties.get('title', False)
                and movie.properties.get('performers', False)
                and movie.properties.get('site', False)
                and 'date' in movie.properties and int(movie.properties['date'].strftime("%s")) > 0
                and movie.properties.get('id', 0) > 0)


def movie_is_empty(movie):
    return bool(not movie.properties.get('title', True)
                and not movie.properties.get('performers', True)
                and not movie.properties.get('site', True)
                and ('date' not in movie.properties or int(movie.properties['date'].strftime("%s")) <= 0)
                and movie.properties.get('id', 0) == 0)
