import urllib.request
import json
import os
import pandas as pd


class ReverseGeoCode:

    def __init__(self, link='http://nominatim.openstreetmap.org/reverse.php?',
                 query='lat=%f&lon=%f&zoom=10&format=json&accept-language=en', email='geometalab@gmail.com'):
        self.query = query+'&email='+email
        self.fetch = link+self.query
        self.data = None

    def _fetch(self, lat, lon):
        """
        Stores the JSON from the reverse geocoding query

        Parameters
        ----------
        lat
        lon

        Returns
        -------

        """
        fetch = self.fetch % (lat, lon)
        response = urllib.request.urlopen(fetch)
        self.data = json.loads(response.read().decode('utf-8'))
        response.close()

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

    def get_cities_from_file(self, date,
                                   folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Tile_log')):
        """
        Fetches a list of cities in the top trending places

        Parameters
        ----------
        date
        folder

        Returns
        -------

        """
        try:
            df = pd.read_csv(os.path.join(folder, date+'.csv'), sep=';')
            cities = set()
            for lat, lon in zip(df['lat'], df['lon']):
                self._fetch(lat, lon)
                cities.add(self._get_city())
            return cities
        except OSError:
            return False

