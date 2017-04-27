import sqlite3
import pandas as pd
import io
import os

CREATE_QUERY_TP = '''CREATE TABLE trending_places(
                    last_day TEXT,
                    world_or_region TEXT,
                    lat REAL,
                    lon REAL,
                    country_code TEXT,
                    view_last_day NUMERIC,
                    zoom INTEGER,
                    tms_x INTEGER,
                    tms_y INTEGER,
                    t_score REAL,
                    rolling_median NUMERIC,
                    abs_med NUMERIC,
                    trending_rank REAL)'''

CREATE_QUERY_IMG = '''CREATE TABLE trending_graphs (
                    Img BLOB,
                    date TEXT,
                    region TEXT)'''

INSERT_QUERY = "INSERT INTO trending_graphs(Img, date, region) VALUES (?,?,?)"
FETCH_QUERY = "SELECT * FROM %s WHERE last_day='%s' and world_or_region='%s'"
FETCH_QUERY_IMG = "SELECT Img FROM %s WHERE date='%s' and region='%s'"
WORLD = 'world'


class TrendingDb:

    def __init__(self, db_name='trending_places.db'):
        db_name_lookup = os.environ.get('DB_NAME', db_name)
        self.con = sqlite3.connect(db_name_lookup)

    def _check_existing(self, table_name):
        """

        Parameters
        ----------
        table_name

        Returns
        -------
        True is the table exists otherwise returns False
        """
        with self.con:
            cur = self.con.cursor()
            cur.execute("SELECT * FROM sqlite_master WHERE name ='%s' and type='table'" % table_name)
            if len(cur.fetchall()):
                cur.close()
                return True
            else:
                cur.close()
                return False

    def _read_img(self, file):
        """

        Parameters
        ----------
        file

        Returns
        -------
        An image buffer in bytes that can be stored in DB

        """
        try:
            data = open(file, "rb")
            img = data.read()
            return img
        except IOError:
            return False

    def _write_img(self, data, file):
        """
        Writes an image from a byte buffer

        Parameters
        ----------
        data
        file

        Returns
        -------
        True if Image is written out successfully else return False.
        """
        try:
            fout = open(file, 'wb')
            fout.write(data)
            return True
        except IOError as e:
            print(e)
            return False
        except TypeError:
            if fout:
                fout.close()
            return False

    def create_table(self, query):
        """
        CREATES table

        Parameters
        ----------
        query

        Returns
        -------

        """
        with self.con:
            cur = self.con.cursor()
            cur.execute(query)
            self.con.commit()
        cur.close()

    def update_table_img(self, img_plot, date, region=WORLD, table_name='trending_graphs'):
        """
        Adds an image to a table, also creating it if it doesn't exist.

        Parameters
        ----------
        img_plot
        date
        region
        table_name

        Returns
        -------

        """
        if not self._check_existing(table_name):
            self.create_table(CREATE_QUERY_IMG)
        buf = io.BytesIO()
        img_plot.savefig(buf, format='png')
        with self.con:
            cur = self.con.cursor()
            buf.seek(0)
            cur.execute(INSERT_QUERY, (buf.read(), date, region))
            buf.close()
            self.con.commit()
        cur.close()

    def update_table(self, df, table_name='trending_places'):
        """
        Adds the top N trending places to the database

        Parameters
        ----------
        df
        table_name

        Returns
        -------

        """
        with self.con:
            df.to_sql(table_name, self.con, index=True, if_exists='append')
            self.con.commit()

    def retrieve_data_img(self, date, file_out, region=WORLD, table_name='trending_graphs'):
        """
        Fetches an image from the Database and saves it on file

        Parameters
        ----------
        date
        region
        file_out
        table_name

        Returns
        -------

        """
        with self.con:
            cur = self.con.cursor()
            data = cur.execute(FETCH_QUERY_IMG % (table_name, date, region)).fetchone()
            cur.close()
        if data:
            return self._write_img(data[0], file_out)
        else:
            return False

    def retrieve_data(self, date, world_or_region=WORLD, table_name='trending_places'):
        """
        Fetched records saved in a Database

        Parameters
        ----------
        date
        world_or_region
        table_name

        Returns
        -------
        pandas data frame
        """
        with self.con:
            return pd.read_sql(FETCH_QUERY % (table_name, date, world_or_region),
                               self.con, parse_dates=['last_day'])

    def Query(self, query):
        """
        For any general query on the database

        Parameters
        ----------
        query

        Returns
        -------

        """
        with self.con:
            cur = self.con.cursor()
            data = cur.execute(query).fetchall()
            cur.close()
        return data

    def del_table(self, table_name):
        """
        Delete the specified table from the DB

        Parameters
        ----------
        table_name

        Returns
        -------

        """
        with self.con:
            cur = self.con.cursor()
            if self._check_existing(table_name=table_name):
                cur.execute("DROP TABLE %s" % table_name)
            cur.close()
            return True
        return False

    def __del__(self):
        self.con.close()
