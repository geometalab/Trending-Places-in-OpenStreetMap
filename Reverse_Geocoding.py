import urllib.request
import json
import os
from Database import TrendingDb


class ReverseGeoCode:

    def __init__(self, link='http://nominatim.openstreetmap.org/reverse.php?',
                 query='lat=%f&lon=%f&zoom=%d&format=json&accept-language=en', email='geometalab@gmail.com'):
        self.query = query + '&email=' + email
        self.query_from_id = 'osm_id=%f&osm_type=%s&format=json&accept-language=en&email=' + email
        self.fetch_from_id = link + self.query_from_id
        self.fetch = link + self.query
        self.data = None

    def _fetch_osmid(self, osm_id, osm_type):
        """
        Stores JSON from osm_id and osm_type geocoding
        """
        if osm_type not in ['N', 'R', 'W']:
            raise Exception('Correct osm_type with N W or R')
        fetch = self.fetch_from_id % (osm_id, osm_type)
        response = urllib.request.urlopen(fetch)
        self.data = json.loads(response.read().decode('utf-8'))
        response.close()
        if 'error' in self.data.keys():
            raise Exception('Wrong query, please check again')

    def _fetch(self, lat, lon, zoom):
        """
        Stores the JSON from the reverse geocoding query

        Parameters
        ----------
        lat
        lon

        Returns
        -------

        """
        fetch = self.fetch % (lat, lon, zoom)
        response = urllib.request.urlopen(fetch)
        self.data = json.loads(response.read().decode('utf-8'))
        response.close()
        if 'error' in self.data.keys():
            self.data['display_name'] = "%.2f %.2f" % (lat, lon)

    def _get_city(self):
        """
        Returns city attribute if it exists, otherwise the display name

        Returns
        -------

        """
        try:
            return self.data['address']['city']
        except KeyError:
            return self.data['display_name']

    def _get_country_code(self):
        """
        Returns country attribute if it exists, otherwise ''

        Returns
        -------

        """
        try:
            return self.data['address']['country_code'].upper()
        except KeyError:
            return ''

    def get_cities_from_file(self, date, region, db=TrendingDb()):
        """
        Fetches a list of cities in the top trending places.
        The csv file must have a lat and lon column in order to reverse geocode

        Parameters
        ----------
        date
        folder
        region
        db

        Returns
        -------

        """
        df = db.retrieve_data(date, world_or_region=region)

        if df.empty:
            return False

        df.sort_values(['trending_rank'], ascending=False, inplace=True)
        cities = list()
        for lat, lon in zip(df['lat'], df['lon']):
            self._fetch(lat, lon, 10)
            cities.append(self._get_city() + '(' + self._get_country_code() + ')')
        return cities

    def get_address_attributes(self, lat, lon, zoom, *args):
        self._fetch(lat, lon, zoom)
        result_dict = {}
        try:
            result_dict['display_name'] = self.data['display_name']
        except KeyError:
            result_dict['display_name'] = "%.2f,%.2f" % (lat, lon)

        for tag in args:
            try:
                result_dict[tag] = self.data['address'][tag]
            except KeyError:
                continue
        return result_dict


class FormatOSMTrendingNames(ReverseGeoCode):

    @staticmethod
    def _check_eng(name):
        if 97 <= ord(name.strip().lower()[0]) <= 122:
            return True
        else:
            return False

    @staticmethod
    def _manipulate_display_name(name):
        max_len = 20
        name = name.strip()
        list = name.split(',')
        i = 0
        while i < len(list) and not FormatOSMTrendingNames._check_eng(list[i]):
            i += 1
        if i == len(list):
            i -= 1
        if len(list[i].strip()) > max_len:
            return list[i][:max_len - 3].strip() + '...'
        else:
            return list[i].strip()

    def get_cities_from_file(self, date, region, char_limit, db=TrendingDb()):
        """
        Returns formatted city names of the top trending palaces chopped off at the specified character limit,
        and returns False if the output of the trending places does not exist.

        Parameters
        ----------
        date
        char_limit
        folder

        Returns
        -------

        """
        final_names = super(FormatOSMTrendingNames, self).get_cities_from_file(date, region)
        value = ''

        if final_names is False:
            return False

        min_len = 5
        max_len = 16
        ellipsis = '...'

        for name in final_names:
            name, country = name.split('(')
            country = '(' + country
            name = name.strip()

            if name.count(',') > 0:
                name = FormatOSMTrendingNames._manipulate_display_name(name)

            if len(name) > max_len:
                name = name[:max_len - 3]
                name.strip()
                temp = name.split(' ')
                if len(temp[len(temp) - 1]) < min_len:
                    name = name.replace(temp[len(temp) - 1], '').strip()
                name += ellipsis
            else:
                name += ' '

            if len(value + name + country + ', ') <= char_limit:
                value += name + country + ', '
            else:
                if len(value + name + country) <= char_limit:
                    value += name + country
                else:
                    value = value[:value.rfind(', ')]
                final_len = len(value + ellipsis)
                if final_len > char_limit:
                    value = value[:char_limit - final_len] + ellipsis
                else:
                    value += ellipsis
                break
        if value.endswith(', '):
            value = value[:value.rfind(', ')]
        return value

    @staticmethod
    def get_trending_graph(date, region,
                           folder=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               'Tile_log'), db=TrendingDb()):
        if not os.path.exists(folder):
            os.makedirs(folder)
        img = os.path.join(folder, 'Trending_Graphs.png')
        return db.retrieve_data_img(date, img, region=region) and img
