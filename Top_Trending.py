import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
import datetime as dt
import itertools as it
from Caches import Cache
from Database import TrendingDb
from Reverse_Geocoding import ReverseGeoCode
matplotlib.use('Agg')
import matplotlib.pylab as plt

MAX_DATE = (dt.datetime.now() - dt.timedelta(days = 2)).replace(hour=0, minute=0, second=0, microsecond=0)
MIN_PERIOD = 7
THRESHOLD = 0.5
RESAMPLE = 'resampled'
WORLD = 'world'
cache = Cache()


def check_eng(name):
    if 97 <= ord(name.strip().lower()[0]) <= 122:
        return True
    else:
        return False


def manipulate_display_name(name):
    max_len = 20
    name = name.strip()
    list = name.split(',')
    i = 0
    while i < len(list) and not check_eng(list[i]):
        i += 1
    if i == len(list):
        i -= 1
    if len(list[i].strip()) > max_len:
        return list[i][:max_len - 3].strip() + '...'
    else:
        return list[i].strip()


def plot_graphs(df, trending_daily, day_from, day_to, limit, country_code, folder_out=None):
    days = pd.DatetimeIndex(start=day_from, end=day_to, freq='D')
    for day in days:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        plt.rc('lines', linewidth=2)
        data = trending_daily.get_group(str(day.date()))
        places, clusters = top_trending(data, limit)
        for cluster in clusters:
            places.add(max_from_cluster(cluster, data))
        ax.set_prop_cycle(plt.cycler('color', [plt.cm.Accent(i) for i in np.linspace(0, 1, limit)]))
        for item in places:
            lat, lon, country = item
            result_items = ReverseGeoCode().get_address_attributes(lat, lon,10, 'city', 'country_code')
            if 'city' not in result_items.keys():
                mark = "%s (%s)" % (manipulate_display_name(result_items['display_name']),
                                    result_items['country_code'].upper() if 'country_code' in result_items.keys() else country)
            else:
                if check_eng(result_items['city']):
                    mark = "%s (%s)" % (result_items['city'], result_items['country_code'].upper())
                else:
                    mark = "%.2f %.2f (%s)" % (lat, lon, result_items['country_code'].upper())
            gp = df.loc[item].plot(ax=ax, x='date', y='count', label=mark)
        ax.tick_params(axis='both', which='major', labelsize=10)
        plt.xlabel('Date', fontsize='small', verticalalignment='baseline', horizontalalignment='right')
        plt.ylabel('Total number of views', fontsize='small', verticalalignment='center', horizontalalignment='center', labelpad=6)
        gp.legend(loc='best', fontsize='xx-small', ncol=2)
        gp.set_title('Top 10 OSM trending places on ' + str(day.date()), {'fontsize': 'large', 'verticalalignment': 'bottom'})
        plt.tight_layout()
        db = TrendingDb()
        db.update_table_img(plt, str(day.date()), region=country_code)
        export(places, clusters, data)
        plt.close()


def max_from_cluster(cluster, data):
    highest = -1
    cluster_max = None
    for item in cluster:
        count = data.loc[item, 'count']
        if count > highest:
            highest = count
            cluster_max = item
    return cluster_max


def export(places, clusters, data):
    for cluster in clusters:
        places.add(max_from_cluster(cluster, data))
    frame = pd.DataFrame()
    property = data.groupby(level=[0, 1, 2])
    for item in places:
        frame = pd.concat([frame, property.get_group(item)])
    frame.rename(columns={'date': 'last_day', 'z': 'zoom', 'x': 'tms_x', 'y': 'tms_y',
                          'count': 'view_last_day'}, inplace=True)
    frame.index.names = ['lat', 'lon', 'country_code']
    frame['last_day'] = frame['last_day'].dt.date
    db = TrendingDb()
    db.update_table(frame)


def identify_cluster(trending_places):
    places = trending_places.copy()
    clusters = []
    for placeA, placeB in it.combinations(places, 2):
        placeAclust = placeBclust = None
        if abs(placeA[0] - placeB[0]) <= THRESHOLD:
            if abs(placeA[1] - placeB[1]) <= THRESHOLD:
                for cluster in clusters:
                    if placeA in cluster:
                        placeAclust = cluster
                    if placeB in cluster:
                        placeBclust = cluster
                    # if both clusters are identified, break to make the query faster.
                    if placeAclust and placeBclust:
                        # Join the two clusters if they are different
                        if placeAclust != placeBclust:
                            clusters.remove(placeBclust)
                            placeAclust.update(placeBclust)
                        break
                else:
                    # Either one of the places is not in any cluster, or both are not in any cluster
                    if not (placeAclust or placeBclust):
                        clusters.append(set([placeA, placeB]))
                    else:
                        (placeAclust or placeBclust).update(set([placeA, placeB]))
    for cluster in clusters:
        places.difference_update(cluster)
    return places, clusters


def top_trending(data, limit):
    fetch = 0
    head = limit
    topTrending = set()
    upper_limit = len(data)
    while True:
        topTrending.update(set((data[fetch:head]).index.values))
        places, clusters = identify_cluster(topTrending)
        req = limit - len(places) - len(clusters)
        if not req or head > upper_limit:
            break
        fetch = head
        head += req
    return places, clusters


def statistics(df, period):
    df['t_score'] = df.groupby(['lat', 'lon', 'countries'])['count'].apply(
                               lambda x: (x - x.rolling(period, period).mean()) * np.sqrt(period) /
                               x.rolling(period,period).std())
    df['rolling_median'] = df.groupby(['lat', 'lon', 'countries'])['count'].apply(
                                      lambda x: x.rolling(period, period).median())
    df['abs_med'] = df['count'] - df['rolling_median']
    return df


def expand_date_range(df, idx):
    df.set_index('date', inplace=True)
    df = df.reindex(idx)
    df['count'].fillna(0, inplace=True)
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)
    df.reset_index('date', inplace=True)
    return df


# cleaning data-maximum time consumption
def resample_missing_values(df, date, period):
    df.set_index('date', inplace=True)
    # For duplicate values for same coordinates, the maximum value is chosen rather than average.
    df = (df.groupby(['lat', 'lon', 'countries'])).resample('D').max()
    df.reset_index(['lat', 'lon', 'countries'], drop=True, inplace=True)
    df['count'].fillna(0, inplace=True)
    df.groupby(['lat', 'lon', 'countries']).fillna(method='ffill', inplace=True)
    df.groupby(['lat', 'lon', 'countries']).fillna(method='bfill', inplace=True)
    df.reset_index(inplace=True)
    idx = pd.DatetimeIndex(start=date-dt.timedelta(days=(period - 1)), end=date, freq='D')
    new_df = pd.DataFrame()
    for index,group in df.groupby(['lat', 'lon', 'countries']):
        group = expand_date_range(group, idx)
        new_df = pd.concat([new_df, group])
    new_df.rename(columns={'index': 'date'}, inplace=True)
    return new_df


def get_country(df, iso):
    # TODO: Update the value of threshold according to country size for better cluster detection?
    global THRESHOLD
    THRESHOLD = 0
    return df[df['countries'] == iso]


def check_data_validity(df, period):
    if len(df.date.unique()) < period:
        return False
    return True


def analyze_data(stdin, date, period, count, graph, country):
    if not date:
        date = MAX_DATE
    else:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
        date = MAX_DATE if date > MAX_DATE else date
    period = MIN_PERIOD if period < MIN_PERIOD else period
    if not cache.existing(RESAMPLE + str(date.date())):
        tile_data = pd.read_csv(stdin, sep=',', parse_dates=['data'], keep_default_na=False)
        tile_data.rename(columns={'data': 'date'}, inplace=True)
        if not check_data_validity(tile_data, period):
            raise AssertionError('Data is missing')
            exit(0)
        tile_data.drop_duplicates(inplace=True)
        if country:
            tile_data = get_country(tile_data, country)
        tile_data = resample_missing_values(tile_data, date, period)
        if not country:
            cache.dumping(tile_data, RESAMPLE + str(date.date()))
    else:
        tile_data = cache.extracting(RESAMPLE + str(date.date()))
        if country:
            tile_data = get_country(tile_data, country)
    tile_data = statistics(tile_data, period)
    tile_data.set_index(['lat', 'lon', 'countries'], inplace=True)
    high_outliers = tile_data[tile_data['t_score'] >= 3.5]
    high_outliers = high_outliers[high_outliers['abs_med'] >= 1000]
    high_outliers.reset_index(inplace=True)
    high_outliers['trending_rank'] = high_outliers.groupby('date')['abs_med'].apply(lambda x: (x-x.median())/x.median())
    # g=(high_outliers['t_score']-high_outliers['t_score'].min())/(high_outliers['t_score'].max()-high_outliers['t_score'].min())
    # high_outliers['trending_rank'] = g*high_outliers['abs_med']/high_outliers['rolling_median']
    if not country:
        high_outliers['world_or_region'] = WORLD
    else:
        high_outliers['world_or_region'] = country
    high_outliers.set_index(['lat', 'lon', 'countries'], inplace=True)
    high_outliers.sort_values(['date', 'trending_rank'], ascending=False, inplace=True)
    trending_each_day = high_outliers.groupby('date')
    if graph:
        plot_graphs(tile_data, trending_each_day, date, date, count, country or WORLD)
    else:
        solo_places, clustered_places = top_trending(trending_each_day.get_group(str(date.date())), count)
        export(solo_places, clustered_places, high_outliers)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Determine and graph top 10 trending places')
    parser.add_argument('--date',default=None, help='The date to calculate trending places (min 3 days ago)')
    parser.add_argument('--period', type=int, default=7, help='Period of days to analyse trends (min 7)')
    parser.add_argument('--count', type=int,default=10, help='Give the trending country')
    parser.add_argument('--graph', action='store_true',default=False, help='Create the graphs of top n Trending places')
    parser.add_argument('--country', default=None, help='ISO code for country to find trending places within')

    stdin = sys.stdin if sys.version_info.major == 2 else sys.stdin.buffer
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer

    analyze_data(stdin,**parser.parse_args().__dict__)
