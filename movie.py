import re
import logging
import datetime
import os

import utils


class Movie:
    UNLIKELY_NUMBERS = {'quality': [360, 480, 720, 1080, 1440, 2160],
                        'date': list(range(1970, 2030))}
    settings = None

    def __init__(self, file_properties, api=None, scene_properties=None):
        # Filter out dates like 091224 or (20)150101
        self._unlikely_shootid_date_re = re.compile('([01]\d)({})({})'.format(
            '|'.join(['{:02}'.format(i) for i in range(1, 13)]),
            '|'.join(['{:02}'.format(i) for i in range(1, 32)])
        ))
        self.api = api

        if type(file_properties) is dict:
            self.file_properties = utils.FileProperties(**file_properties)
        else:
            self.file_properties = file_properties

        if type(scene_properties) is dict:
            self.scene_properties = utils.SceneProperties(**scene_properties)
        elif type(scene_properties) is utils.SceneProperties:
            self.scene_properties = scene_properties
        else:
            self.scene_properties = utils.SceneProperties()

        if self.settings is None:
            logging.warning('Settings were not set by calling class! This will break!')

    def serialize(self):
        return {'file_properties': self.file_properties.serialize(),
                'api': self.api.name if self.api is not None else None,
                'scene_properties': self.scene_properties.serialize()}

    def update_details(self):
        if self.api is None:
            logging.info('"{}" - No API, skipped.'.format(self.file_properties.print_base_name()))
            return

        result = None
        shootid, sure = self.get_shootid(self.file_properties.file_path)
        if shootid:
            results = self.api.query('shoots', 'shootid', shootid)
            result = self.interactive_confirm(results, sure=sure)

        if not result:
            logging.info('"{}" - No result found, going interactive...'.format(self.file_properties.print_base_name()))
            result = self.interactive_query()

        if result:
            self.scene_properties.update(result)
        else:
            logging.info('"{}" - Nothing found, leaving untagged'.format(self.file_properties.print_base_name()))

    def get_shootid(self, file_path):
        try:
            shootid_cv = self.api.get_shootid_through_image_recognition(file_path)
        except AttributeError:
            shootid_cv = 0
        try:
            shootid_md = self.api.get_shootid_through_metadata(file_path)
        except AttributeError:
            shootid_md = 0

        shootid_nr = 0
        shootids_nr = self.get_shootids_from_filename(file_path)
        if len(shootids_nr) > 1:
            if shootid_cv and shootid_cv in shootids_nr:
                shootid_nr = shootid_cv
            elif shootid_cv and shootid_md in shootids_nr:
                shootid_nr = shootid_md
            else:
                shootid_nr = self.interactive_choose_shootid(shootids_nr)
        elif shootids_nr:
            shootid_nr = shootids_nr[0]

        logging.debug('Found shootids - cv: {}; md: {}; nr: {}'.format(shootid_cv, shootid_md, shootid_nr))
        sure = False
        shootid = 0
        if (shootid_nr > 0 and shootid_nr == shootid_cv) or shootid_cv > 0 or shootid_md > 0:
            # Clear solution
            sure = True
            shootid = shootid_cv if shootid_cv else shootid_md
        elif shootid_nr:
            # No image recognition, but a number is found => pre shootid-tagging in the video
            # Image recognition yields "-1" (error in video file), so trust shootid
            if shootid_nr < 1000:
                logging.info('File "{}" has shootid<1000. Check this, could be wrongly detected'.format(
                    self.file_properties.print_base_name()))
            elif shootid_nr > 8000 and shootid_cv != -1:
                logging.info('File "{}" has the wrong API or is (mildly) corrupted'.format(
                    self.file_properties.print_base_name()))
            else:
                sure = True

            shootid = shootid_nr
        logging.debug('Chose shootid {}, sure: {}'.format(shootid, sure))
        return shootid, sure

    def get_shootids_from_filename(self, file_path):
        base_name = os.path.basename(file_path)
        search_shootid = []

        # \D does not match ^|$, so we pad it with something irrelevant
        search_name = '%' + base_name + '%'

        search_match = 1
        while search_match:
            search_name = search_name[search_match.end() - 1:] if search_match != 1 else search_name

            # Search with re.search instead of re.findall, as pre/post can be interleaved and regexps capture
            search_match = re.search(r"(\D)(\d{2,6})(\D)", search_name)
            if search_match:
                pre_, k, post_ = search_match.groups()
                shootid = int(k)
                if shootid in self.UNLIKELY_NUMBERS['date']:
                    continue
                if self._unlikely_shootid_date_re.search(k):
                    logging.debug('Most likely no shootid ({}), but a date. Skipping...'.format(k))
                    continue
                if shootid < 200:
                    continue
                if shootid in self.UNLIKELY_NUMBERS['quality'] and (pre_ != '(' or post_ != ')'):
                    logging.debug('Most likely no shootid ({}{}{}), but a quality. Skipping...'.format(pre_, k, post_))
                    continue
                if pre_ in ['(', '['] and post_ in [')', ']']:
                    return [shootid]

                search_shootid.append(shootid)

        if len(search_shootid) > 1:
            logging.info('Multiple Shoot IDs found')

        return search_shootid

    def interactive_query(self):
        if not self.settings.interactive:
            return {}

        logging.info('Unable to find anything to work automatically. Please help with input')

        user_input = "don't stop yet :)"
        while user_input:
            logging.info('Movie in Question: {}'.format(self.file_properties.file_path))
            user_input = input('Please input an ID, a data or a name of the movie in the format:\n  ' +
                               'ID: i<id>; Date: d<date YYYY-mm-dd>; '
                               'Performer: p<Name>; Name: <name>; Abort: <empty string>\n   ').strip()
            if user_input.startswith('i'):
                id_ = int(user_input[1:]) if user_input[1:].isdigit() else 0
                if not id_:
                    logging.info('"{}" was no number, please repeat!'.format(user_input[1:]))
                    continue
                results = self.api.query('shoots', 'shootid', id_)
                if not results:
                    logging.info('No results found, try something other')
                    continue
                result = self.interactive_confirm(results)
                if result is not None:
                    return result

            elif user_input.startswith('d'):
                date_string = user_input[1:].replace('.', '-')
                try:
                    if date_string.isdigit():
                        date_ = datetime.datetime.strptime(date_string, '%s').date()
                    else:
                        date_ = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
                    logging.info('Date interpreted as {}'.format(date_))
                except (ValueError, AttributeError):
                    logging.info('Could not parse date "{}".'.format(date_string))
                    continue
                date_ = date_.strftime('%s')
                results = self.api.query('shoots', 'date', str(date_))
                if not results:
                    logging.info('No results found, try something other')
                    continue
                result = self.interactive_confirm(results)
                if result is not None:
                    return result

            elif user_input.startswith('p'):
                performer_string = user_input[1:]
                if ',' not in performer_string:
                    results = self.api.query('performers', 'name', performer_string)
                    if not results:
                        logging.info('No results found, try something other')
                        continue
                    result = self._interactive_select_match(results)
                    if not result or 'number' not in result:
                        continue
                    results = self.api.query_api('shoots', 'performers_number', result['number'])
                else:
                    # Query API, since it has aggregated functions (like performers_names), the cache is just a list
                    results = self.api.query_api('shoots', 'performers_names', performer_string)
                result = self.interactive_confirm(results)
                if result is not None:
                    return result

            elif user_input:
                name_ = user_input
                results = self.api.query('shoots', 'title', name_)
                result = self.interactive_confirm(results)
                if result is not None:
                    return result

            else:
                break

        return {}

    def interactive_confirm(self, results, sure=False):
        result = self._interactive_select_match(results)
        if result and result.get('exists', True):
            logging.info('old: {}'.format(self.file_properties.base_name))
            logging.info('new: {}'.format(self.format_shoot_dict(result)))
            answer = input('Is this okay? Y, n?') if self.settings.interactive and not sure else 'Y'
            if not answer or answer.lower().startswith('y'):
                return result
        return None

    def _interactive_select_match(self, results):
        """ Print all matches of shoot/Performers/site and let the user choose one.

        Returns the first element when noninteractive or just 1 element
        Returns the chosen element when something is chosen
        Returns {} when the user chooses to abort
        Returns the input when the input is not a list (e.g. no need for selecting)
        """
        if type(results) == list:
            if self.settings.interactive and len(results) > 1:
                results.sort(key=lambda f: f.get('date', 0))
                logging.info('Possible matches:')
                logging.info('\t0: None of the below')
                for i, result in enumerate(results):
                    logging.info('\t{}: {}'.format(i + 1, self.format_result_dict(result)))

                while True:
                    selection = input('Select the correct number: ')
                    if not selection or selection == '0':
                        return {}
                    if selection.isdigit() and int(selection) <= len(results):
                        return results[int(selection) - 1]

            if len(results) == 0:
                return results

            return results[0]

        return results

    def interactive_choose_shootid(self, results):
        """ Print all shootids and let the user choose one.

        Returns the biggest element when noninteractive or just 1 element
        Returns the chosen element when something is chosen
        Returns 0 when the user chooses to abort
        Returns 0 when the input is not a list (e.g. doesn't fit)
        """
        if not self.settings.interactive or len(results) == 1:
            return max(results)

        results.sort()
        logging.info('Choose the Shoot ID of file "{}"'.format(self.file_properties.file_path))
        logging.info('\t0: None of the below')
        for i, result in enumerate(results):
            logging.info('\t{}: {}'.format(i + 1, result))

        while True:
            selection = input('Select the correct number or an own shootid: ')
            if not selection or selection == '0':
                break
            if selection.isdigit():
                sel = int(selection)
                return results[sel - 1] if sel <= len(results) else sel

        return 0

    def format_result_dict(self, result):
        if 'is_partner' in result.keys():
            return result.get('name', '<No Name>')
        if 'number' in result.keys():
            return '{} ({}) - [{}]'.format(result.get('name', '<No Name>'), result.get('number', ''), str(result)[:40])
        if 'shootid' in result.keys():
            if not result.get('exists', False):
                return '<Shootid {} does not exist>'.format(result.get('shootid'))
            else:
                return self.format_shoot_dict(result)

    @staticmethod
    def format_shoot_dict(result):
        scene_properties_tmp = utils.SceneProperties(**result)
        return str(scene_properties_tmp)

    def __eq__(self, other):
        if self.scene_properties.is_empty() and other.scene_properties.is_empty():
            return self.file_properties.base_name == other.file_properties.base_name
        return (self.file_properties.file_path == other.file_properties.file_path
               or self.scene_properties == other.scene_properties)

    def __str__(self):
        if self.scene_properties.is_empty():
            if self.file_properties.base_name.startswith('[<untagged>]'):
                return '{p.base_name}{p.extension}'.format(p=self.file_properties).replace('/', '_')
            return '[<untagged>] {p.base_name}{p.extension}'.format(
                p=self.file_properties).replace('/', '_')

        ret = str(self.scene_properties)
        if not self.scene_properties.is_filled():
            ret += ' | [<incompletely_tagged>] {p.base_name}{p.extension}'.format(p=self.file_properties)

        ret += self.file_properties.extension
        return ret.replace('/', '_')

    def __bool__(self):
        return self.scene_properties.is_filled()

if __name__ == '__main__':
    import sys
    path = sys.argv[1]
    logging.basicConfig(format='%(funcName)-30s: %(message)s',
                        level=logging.DEBUG)
    file_properties_ = utils.FileProperties(path, storage_root_path='')
    settings_ = utils.Settings({'shootid_template_dir': 'apis/templates'})
    Movie.settings = settings_
    m = Movie(file_properties=file_properties_, api=settings_.apis.get('Kink.com', None), scene_properties=None)

    m.update_details()

    print(m)