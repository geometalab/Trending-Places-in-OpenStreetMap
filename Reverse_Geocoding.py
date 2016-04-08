import urllib.request
import json
import os
import pandas as pd


class ReverseGeoCode:

    def __init__(self, link='http://nominatim.openstreetmap.org/reverse.php?',
                 query='lat=%f&lon=%f&zoom=%d&format=json&accept-language=en', email='geometalab@gmail.com'):
        self.query = query+'&email='+email
        self.query_from_id = 'osm_id=%f&osm_type=%s&format=json&accept-language=en&email='+email
        self.fetch_from_id = link+self.query_from_id
        self.fetch = link+self.query
        self.data = None


    def _fetch(self, osm_id, osm_type):
        """
        Stores JSON from osm_id and osm_type geocoding
        """
        if osm_type not in ['N', 'R', 'W']:
            raise Exception ('Correct osm_type with N W or R')
        fetch = self.fetch_from_id % (osm_id, osm_type)
        response = urllib.request.urlopen(fetch)
        self.data = json.loads(response.read().decode('utf-8'))
        response.close()
        if 'error' in self.data.keys():
            raise Exception ('Wrong query, please check again')


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
            raise Exception ('Wrong query, please check again')

    def _get_city(self):
        """
        Returns city attribute if it exists, otherwise the display name

        Returns
        -------

        """
        try:
            return self.data['address']['city']
        except KeyError:
            return "%.2f,%.2f" % (self.data['lat'], self.data['lon'])

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


    def get_cities_from_file(self, date,
                                   folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Tile_log')):
        """
        Fetches a list of cities in the top trending places.
        The csv file must have a lat and lon column in order to reverse geocode

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
                cities.add(self._get_city()+'('+self._get_country_code()+')')
            return cities
        except OSError:
            return False


    def get_address_attributes(self, lat, lon, zoom, *args):
        self._fetch(lat, lon, zoom)
        Result_dict={}
        for tag in args:
            try:
               print (tag)
               Result_dict[tag]=self.data['address'][tag]
            except KeyError:
               continue
        return Result_dict

