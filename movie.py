import re
import logging
import datetime
import os


class Movie:
    UNLIKELY_NUMBERS = {'quality': [360, 480, 720, 1080, 1440, 2160],
                        'date': list(range(1970, 2030))}
    settings = None

    def __init__(self, file_path, api, properties=None):
        self.file_path = file_path
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
        self.properties = {'title': '', 'performers': [], 'date': datetime.date(1970, 1, 1), 'site': '', 'shootid': 0}
        self.properties.update(properties)

        if self.settings is None:
            logging.warning('Settings were not set by calling class! This will break!')

    def update_details(self):
        if self.api is None:
            return
        shootid_nr = 0
        shootids_nr = self.get_shootids(self.base_name)
        shootid_cv = self.api.get_shootid_through_image_recognition(self.file_path)
        if shootids_nr:
            if len(shootids_nr) > 1:
                shootid_nr = self.interactive_choose_shootid(shootids_nr)
            else:
                shootid_nr = shootids_nr[0]

        if shootid_nr == shootid_cv or shootid_cv > 0:
            # Clear solution
            results = self.api.query_for_id(shootid_cv)
            result = self.interactive_confirm(results)
            if result:
                self.properties.update(result)
                return
        elif shootid_nr:
            # No image recognition, but a number is found => pre shootid-tagging in the video
            # Image recognition yields "-1" (error in video file), so trust shootid
            if shootid_nr < 8000 or shootid_cv == -1:
                results = self.api.query_for_id(shootid_nr)
                result = self.interactive_confirm(results)
                if result:
                    self.properties.update(result)
                    return
            else:
                logging.info('File "{}" most likely has the wrong API or is (mildly) corrupted'.format(self.base_name))

        t_ = re.search(r"\d{4}\W\d{1,2}\W\d{1,2}", self.base_name)
        likely_date = t_.group(0) if t_ else ''
        result = self.interactive_query(likely_date)
        self.properties.update(result)

    def get_shootids(self, base_name):
        search_shootid = []

        # \D does not match ^|$, so we pad it with something irrelevant
        for pre_, k, post_ in re.findall(r"(\D)(\d{2,6})(\D)", '%'+base_name+'%'):
            shootid = int(k)
            if shootid in self.UNLIKELY_NUMBERS['date']:
                logging.debug('Most likely no shootid ({}), but a year. Skipping...'.format(k))
                continue
            if self._unlikely_shootid_date_re.search(k):
                logging.debug('Most likely no shootid ({}), but a date. Skipping...'.format(k))
                continue
            if shootid < 200:
                logging.debug('Most likely no shootid ({}), but a day/month/age/number. Skipping...'.format(k))
                continue
            if shootid in self.UNLIKELY_NUMBERS['quality'] and (pre_ != '(' or post_ != ')'):
                logging.debug('Most likely no shootid ({}{}{}), but a quality. Skipping...'.format(pre_, k, post_))
                continue

            search_shootid.append(shootid)

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
                results = self.api.query_for_id(id_)
                result = self.interactive_confirm(results)
                if result:
                    return result
            elif user_input.startswith('d'):
                date_string = user_input[1:]
                try:
                    date_ = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
                    print('Date interpreted as {}'.format(date_))
                except (ValueError, AttributeError):
                    print('Could not parse date "{}".'.format(date_string))
                    continue
                results = self.api.query_for_date(date_)
                result = self.interactive_confirm(results)
                if result:
                    return result
            elif user_input:
                name_ = user_input
                results = self.api.query_for_name(name_)
                result = self.interactive_confirm(results)
                if result:
                    return result
            else:
                print('Leaving movie "{}" untagged.'.format(self.base_name))
                continue

        return {}

    def interactive_confirm(self, results):
        if self.settings.interactive and len(results) != 1:
            print('Possible matches:\n')
            print('\t0: None of the below')
            for i, result in enumerate(results):
                print('\t{}: {}'.format(i+1, format_properties(result)))
            selection = input('Select the correct number')
            result = results[selection+1] if selection != 0 else {}
        else:
            result = results[0]

        if self._interactive_confirm_helper(result):
            return result

    def _interactive_confirm_helper(self, result):
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
                and self.properties.get('shootid', 0) == other.properties.get('shootid', 0))

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

    ret += '{site} - {date} - {title} [{perfs}] ({shootid}){ext}'.format(
        site=movie.properties.get('site', '').replace(' ', ''),
        date=movie.properties.get('date', ''),
        title=movie.properties.get('title', ''),
        perfs=', '.join(movie.properties.get('performers', '')),
        shootid=movie.properties.get('shootid', ''),
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
                and movie.properties.get('shootid', 0) > 0)


def movie_is_empty(movie):
    return bool(not movie.properties.get('title', True)
                and not movie.properties.get('performers', True)
                and not movie.properties.get('site', True)
                and ('date' not in movie.properties or int(movie.properties['date'].strftime("%s")) <= 0)
                and movie.properties.get('shootid', 0) == 0)
