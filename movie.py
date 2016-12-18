import utils
import re
import logging

class Movie():
    UNLIKELY_NUMBERS = {'quality':[360,480,720,1080,1440,2160], 'years':range(1950,2050)}

    def __init__(self, file_path, properties={}, last_query_time=0):
        self.file_path = file_path
        self.last_query_time = last_query_time
        self.properties = properties

        if properties:
            return

        base_path, filename = file_path.rsplit('/',1)
        base_path, dirname = base_path.rsplit('/',1) if '/' in base_path else ('', base_path)
        base_name, extension = filename.rsplit('.',1)

        # TODO: now try to find out name
        # Search by ID:
        # first, remove all numbers not likely to be ids
        search_kinkid = re.findall(r"\d{4,5}", base_name)
        if len(search_kinkid) > 1:
            unlikely = [id for id in search_kinkid if id in self.UNLIKEY_NUMBERS]
        for id in search_kinkid:
            if id in self.UNLIKELY_NUMBERS:
                logging.info('Title in ')
            api_response = utils.query_api('imdbID', search_imdbid.group(0))
            if api_response:
                self.properties = api_response
        ...