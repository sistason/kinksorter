import re
import logging
import datetime
import os
import cv2
import numpy as np
import subprocess
import tempfile


class Movie():
    UNLIKELY_NUMBERS = {'quality': [360,480,720,1080,1440,2160], 'date': list(range(1999, 2030))+list(range(0, 32))}

    def __init__(self, file_path, settings, properties=None):
        self.file_path = file_path
        self._unlikely_numbers_re = re.compile('|'.join(str(i) + 'p' for i in self.UNLIKELY_NUMBERS['quality']))
        self.settings = settings

        base_path_, filename_ = os.path.split(file_path)
        _, self.subdirname = os.path.split(base_path_)
        self.base_name, self.extension = os.path.splitext(filename_)

        if properties is None:
            properties = {}
        self.properties = {'title': '', 'performers': [], 'date': datetime.date(1970, 1, 1), 'site': '', 'id': 0}
        self.properties.update(properties)

        self.api = self.get_correct_api()

    def get_correct_api(self):

        return None

    def update_details(self):
        shootids = self.get_shootids(self.base_name)
        if shootids:
            if len(shootids) > 1:
                shootid = self.interactive_choose_shootid(shootids)
            else:
                shootid = shootids[0]
        else:
            shootid = self.get_shootid_through_image_recognition()

        if shootid:
            result = self.api.query_for_id(shootid)
            if self.interactive_confirm(result):
                self.properties.update(result)
        else:
            t_ = re.search(r"\d{4}\W\d{1,2}\W\d{1,2}", self.base_name)
            likely_date = t_.group(0) if t_ else ''
            self.properties.update(self.interactive_query(likely_date))

    def get_shootids(self, base_name):
        base_name = re.sub(self._unlikely_numbers_re, '', base_name)
        search_shootid = []

        # FIXME: \d{2,6} scrambles numbers, (?:\D|^)(\d{2,6})(?:\D|$) has problems
        for k in re.findall(r"\d+", base_name):
            if 2 <= len(k) <= 6 and int(k) not in self.UNLIKELY_NUMBERS['date']:
                search_shootid.append(int(k))

        if len(search_shootid) > 1:
            logging.info('Multiple Shoot IDs found, choose one')
        return search_shootid

    def interactive_query(self, likely_date=''):
        if not self.settings['interactive']:
            return {}

        print('Unable to find anything to work automatically. Please help with input')
        print('Movie in Question:', self.file_path, 'Likely date:', likely_date)

        user_input = "don't stop yet :)"
        while user_input:
            user_input = input('Please input an ID, a data or a name of the movie in the format:\n' +
                               '  ID: i<id>; Date: d<date YYYY-mm-dd>; Name: <name>; Abort: <empty string>\n   ').strip()
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
        answer = input('Is this okay? Y, n?') if self.settings['interactive'] else 'Y'
        return True if not answer or answer.lower().startswith('y') else False

    def interactive_choose_shootid(self, likely_ids):
        if not self.settings['interactive']:
            return max(likely_ids)

        id_ = None
        while not id_ or not id_.isdigit():
            try:
                id_ = input('Choose the Shoot ID of file "{}". Likely are:\n\t{}'.format(
                                        self.file_path, '\n\t'.join(map(str, likely_ids))))
            except KeyboardInterrupt:
                return 0
        return int(id_)

    def get_shootid_through_image_recognition(self):
        capture = cv2.VideoCapture(self.file_path)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not frame_count:
            return 0
        template = self.settings.get('shootid_template', None)
        if template is None:
            return 0
        fps = capture.get(cv2.CAP_PROP_FPS)
        ret = capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count - int(4*fps))
        frame_list = []
        while ret:
            ret, frame_ = capture.read()
            if ret:
                frame_list.append((frame_.max(), frame_))

        if not frame_list:
            return 0
        frame_list.sort(key=lambda f: f[0])
        best_frame = frame_list[-1][1]

        red_frame = best_frame[:, :, 2]

        if template.dtype != np.dtype('uint8'):
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(red_frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < 0.7:
            return 0

        template_height, template_width = template.shape
        shootid_crop = red_frame[max_loc[1]:max_loc[1]+template_height, max_loc[0]+template_width:]

        shootid = self.recognize_shootid(shootid_crop)
        if not shootid:
            pass
            #self.debug_frame(shootid_crop)

        return shootid

    def recognize_shootid(self, shootid_img):
        # FIXME: filepath-independence by piping the image?
        tmp_image = '/tmp/kinksorter_shootid.jpeg'
        cv2.imwrite(tmp_image, shootid_img)
        output = subprocess.run(['tesseract', tmp_image, 'stdout', 'digits'], stdout=subprocess.PIPE)
        if output.stdout is not None and output.stdout.strip().isdigit():
            return int(output.stdout)
        return 0

    def debug_frame(self, frame):
        cv2.imwrite('/tmp/test.jpeg', frame)
        os.system('eog /tmp/test.jpeg 2>/dev/null')

    def __eq__(self, other):
        if movie_is_empty(self) and movie_is_empty(other):
            return self.base_name == other.base_name
        return (not (movie_is_empty(self) and movie_is_empty(other))
                and self.properties.get('title','') == other.properties.get('title','')
                and self.properties.get('performers', []) == other.properties.get('performers', [])
                and self.properties.get('date', None) == other.properties.get('date', None)
                and self.properties.get('site', '') == other.properties.get('site', '')
                and self.properties.get('id',0) == other.properties.get('id',0))

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
    def __init__(self, p,b=''):
        self.properties=p
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


