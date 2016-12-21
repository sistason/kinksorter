import api
import re
import logging
import datetime


class Movie():
    UNLIKELY_NUMBERS = {'quality':[360,480,720,1080,1440,2160], 'years':range(1950,2050)}
    properties = {'title': '', 'performers': [], 'date': datetime.date(1970, 1, 1), 'site': '', 'id': 0}

    def __init__(self, file_path, api, properties={}):
        self.file_path = file_path
        self.properties.update(properties)
        self.api = api
        self.ALL_UNLIKELY_NUMBERS = []
        [self.ALL_UNLIKELY_NUMBERS.extend(i) for i in self.UNLIKELY_NUMBERS.values()]

        if properties:
            return

        base_path, filename = file_path.rsplit('/',1)
        base_path, dirname = base_path.rsplit('/',1) if '/' in base_path else ('', base_path)
        self.base_name, self.extension = filename.rsplit('.',1)

        kinkids = self.get_kinkids(self.base_name)
        if kinkids:
            if len(kinkids) > 1:
                kinkid = self.interactive_choose_kinkid(kinkids)
            else:
                kinkid = kinkids[0]
        else:
            kinkid = self.get_kinkid_through_image_recognition()

        if kinkid:
            result = api.query('id', kinkid)
            if self.interactive_confirm(result):
                self.properties.update(result)
        else:
            t_ = re.search(r"\d{4}\W\d{1,2}\W\d{1,2}", self.base_name)
            likely_date = t_.group(0) if t_ else ''
            self.properties = self.interactive_query(likely_date)

    def get_kinkids(self, base_name):
        base_name = re.sub('|'.join(str(i)+'p' for i in self.UNLIKELY_NUMBERS['quality']),
                           "", base_name)
        search_kinkid = list(map(int, re.findall(r"\d{3,6}", base_name)))

        if len(search_kinkid) > 1:
            likelies = [id for id in search_kinkid if id not in self.ALL_UNLIKELY_NUMBERS]
            if len(likelies) == 1:
                return likelies
            elif len(likelies) > 1:
                logging.info('Multiple likely kink_ids found, choose one')
                return likelies
            else:
                logging.info('No likely kink_id found, choose from all numbers found')
                return search_kinkid

        elif len(search_kinkid) == 1:
            if search_kinkid in self.ALL_UNLIKELY_NUMBERS:
                logging.info('Unlikely')
            return search_kinkid
        return []

    def interactive_query(self, likely_date=''):
        # TODO: query which movie
        """
        new_query = likely_date
        do
          result = query(new_query)
          answer = input($formated_result okay? Y, n, new_query)
          parse_answer
        until not answer
        return result
        """

        if likely_date:
            result = self.api.query('date', likely_date)

        return {}

    def interactive_confirm(self, result):
        print('Is this okay?')
        print('{} -> {}'.format(self.file_path, self.format_movie(result)))
        answer = input('Y, n?')
        return True if not answer or answer.lower().startswith('y') else False

    def interactive_choose_kinkid(self, likely_ids):
        # TODO: Qt
        id_ = None
        while not id_ or not id_.isdigit():
            try:
                id_ = input('Choose the Kink-ID of file "{}". Likely are:\n\t{}'.format(
                                        self.file_path, '\n\t'.join(map(str, likely_ids))))
            except KeyboardInterrupt:
                return 0
        return int(id_)

    def get_kinkid_through_image_recognition(self):
        # TODO: OpenCV Project :)
        return 0

    def format_movie(self, properties):
        return '{site} - {date} - {title} [{perfs}] ({id})'.format(
            site=properties.get('site', ''),
            date=properties.get('date', ''),
            title=properties.get('title', ''),
            perfs=', '.join(properties.get('performers', '')),
            id=properties.get('id', ''))

    def __eq__(self, other):
        return (self.properties.get('title','') == other.properties.get('title','')
                and self.properties.get('performers', []) == other.properties.get('performers', [])
                and self.properties.get('date', None) == other.properties.get('date', None)
                and self.properties.get('site', '') == other.properties.get('site', '')
                and self.properties.get('id',0) == other.properties.get('id',0))

    def __str__(self):
        return self.format_movie(self.properties)

    def __bool__(self):
        return bool(self.properties.get('title',False)
                and self.properties.get('performers', False)
                and self.properties.get('site', False)
                and 'date' in self.properties and int(self.properties['date'].strftime("%s")) > 0
                and self.properties.get('id', 0) > 0)
