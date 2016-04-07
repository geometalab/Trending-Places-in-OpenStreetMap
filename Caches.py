import os
import pandas as pd


class Cache:

    def __init__(self, folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Cache')):
        self.folder = folder
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def dumping(self, df, name):
        """
        Saves processed df in cache file

        Parameters
        ----------
        df
        name

        Returns
        -------

        """
        dump_path = os.path.join(self.folder, name+'.csv')
        df.to_csv(dump_path, sep=';', index=False)

    def extracting(self, name):
        """
        Retrieves a data frame from the file

        Parameters
        ----------
        name

        Returns
        -------

        """
        try:
            extract_path = os.path.join(self.folder, name+'.csv')
            return pd.read_csv(extract_path, sep=';', parse_dates=['date'], keep_default_na=False)
        except IOError:
            return False

    def existing(self, name):
        """
        Check is a copy exists in cache

        Parameters
        ----------
        name

        Returns
        -------

        """
        extract_path = os.path.join(self.folder, name+'.csv')
        return os.path.exists(extract_path)

