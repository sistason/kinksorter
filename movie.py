import utils
import re
import logging

class Movie():
    UNLIKELY_NUMBERS = {'quality':[360,480,720,1080,1440,2160], 'years':range(1950,2050)}

    def __init__(self, file_path, properties={}, last_query_time=0):
        self.file_path = file_path
        self.last_query_time = last_query_time
        self.properties = properties
        self.ALL_UNLIKELY_NUMBERS = []
        [self.ALL_UNLIKELY_NUMBERS.extend(i) for i in self.UNLIKELY_NUMBERS]

        if properties:
            return

        base_path, filename = file_path.rsplit('/',1)
        base_path, dirname = base_path.rsplit('/',1) if '/' in base_path else ('', base_path)
        base_name, extension = filename.rsplit('.',1)

        search_kinkid = re.findall(r"\d{4,5}", base_name)
        kinkid = 0
        if len(search_kinkid) > 1:
            likely = [id for id in search_kinkid if id not in self.ALL_UNLIKELY_NUMBERS]
            logging.info('Multiple likelies, choose one')
            kinkid = utils.interactive_choose_kinkid(file_path, likely)

        elif len(search_kinkid) == 1:
            kinkid = search_kinkid.group(0)
            if kinkid in self.ALL_UNLIKELY_NUMBERS:
                logging.info('Unlikely')

        if kinkid:
            result = utils.query_api('id', kinkid)
            if utils.interactive_confirm(file_path, result):
                self.properties = result
                return

        t_ = re.search(r"\d{4}\W\d{1,2}\W\d{1,2}", base_name)
        likely_date = t_.group(0) if t_ else ''
        self.properties = utils.interactive_query(file_path, likely_date)