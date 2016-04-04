import sys
import argparse
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pylab as plt
import datetime as dt
import itertools as it
import os

MAX_DATE = dt.datetime.now()-dt.timedelta(days=3)
MIN_PERIOD=7
THRESHOLD=0.5


def plot_graphs(df, trending_daily, day_from, day_to,limit,folder_out=None):
    days = pd.DatetimeIndex(start=day_from, end=day_to, freq='D')
    if not folder_out:
        folder_out=os.path.join(os.path.dirname(os.path.abspath(__file__)),'Tile_log')
    else:
        folder_out=os.path.join(folder_out,'Tile_log')
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)
    pp=PdfPages(os.path.join(folder_out,'Trending_Graphs.pdf'))
    for day in days:
        fig=plt.figure()
        ax=fig.add_subplot(111)
        data=trending_daily.get_group(str(day))
        places,clusters=top_trending(data,limit)
        for cluster in clusters:
            places.add(max_from_cluster(cluster,data))
        for item in places:
              lat,lon,country=item
              mark="%f %f "% (lat,lon)
              mark=mark+country
              gp=df.loc[item].plot(ax=ax,x='date',y='count', label=mark)
        ax.axvline(x=day.date(),linestyle='dashed',color='red')
        gp.legend(loc='best',fontsize='xx-small')
        gp.set_title(day,{'fontsize': 'xx-small','verticalalignment': 'bottom'})
        plt.savefig(pp,format='pdf')
        xpath= os.path.join(folder_out,str(day.date())+'.csv')
        export_to_csv(places,clusters,data,xpath)
        plt.close()
    pp.close()


def max_from_cluster(cluster, data):
    highest=-1
    cluster_max=None
    for item in cluster:
        count=data.loc[item,'count']
        if count>highest:
            highest=count
            cluster_max=item
    return cluster_max


def export_to_csv(places, clusters, data, stdout):
    for cluster in clusters:
        places.update(cluster)
    frame=pd.DataFrame()
    property=data.groupby(level=[0,1,2])
    for item in places:
        frame=pd.concat([frame,property.get_group(item)])
    frame.to_csv(stdout,sep=';')


def identify_cluster(trending_places):
    places=trending_places.copy()
    clusters=[]
    for placeA,placeB in it.combinations(places,2):
        placeAclust=placeBclust=None
        if abs(placeA[0]-placeB[0]) <=THRESHOLD:
            if abs(placeA[1]-placeB[1]) <=THRESHOLD:
                for cluster in clusters:
                    if placeA in cluster:
                        placeAclust=cluster
                    if placeB in cluster:
                        placeBclust=cluster
                    #if both clusters are identified, break to make the query faster.
                    if placeAclust and placeBclust:
                        #Join the two clusters if they are different
                        if placeAclust != placeBclust:
                            clusters.remove(placeBclust)
                            placeAclust.update(placeBclust)
                        break
                else:
                    #Either one of the places is not in any cluster, or both are not in any cluster
                    if not (placeAclust or placeBclust):
                        clusters.append(set([placeA,placeB]))
                    else:
                        (placeAclust or placeBclust).update(set([placeA,placeB]))
    for cluster in clusters:
        places.difference_update(cluster)
    return (places, clusters)


def top_trending(data, limit):
    fetch=0
    head=limit
    topTrending=set()
    while True:
        topTrending.update(set((data[fetch:head]).index.values))
        places,clusters=identify_cluster(topTrending)
        req=limit-len(places)-len(clusters)
        if not req:
            break
        fetch=head
        head+=req
    return (places, clusters)

#TODO: try except clean the code
def statistics(df, period):
    df['Tscore']=df.groupby(['lat','lon','countries'])['count'].apply(lambda x: (x-pd.rolling_mean(x,period,period))*np.sqrt(period)/pd.rolling_std(x,period,period))
    df.set_index(['lat','lon','countries'],inplace=True)
    #Temporary solution for the problem in Pandas.
    for index,group in df.groupby(level=[0,1,2]):
        try:
            df.loc[index,'rolling_median']=pd.rolling_median(group['count'],period,period)
        except MemoryError:
            df.loc[index,'rolling_median']=pd.rolling_median(group['count'],period,period)
    df['abs_med']=df['count']-df['rolling_median']
    return df


def expand_date_range(df, idx):
    df.set_index('date',inplace=True)
    df=df.reindex(idx)
    df['count'].fillna(0,inplace=True)
    df.fillna(method='ffill',inplace=True)
    df.fillna(method='bfill',inplace=True)
    df.reset_index('date',inplace=True)
    return df

#cleaning data-maximum time consumption
def resample_missing_values(df, date, period):
    df.set_index('date',inplace=True)
    #For duplicate values for same coordinates, the maximum value is chosen rather than average.
    df=(df.groupby(['lat','lon','countries'])).resample('D',how='max')
    df['count'].fillna(0,inplace=True)
    df.groupby(level=['lat','lon','countries']).fillna(method='ffill',inplace=True)
    df.groupby(level=['lat','lon','countries']).fillna(method='bfill',inplace=True)
    df.reset_index(inplace=True)
    idx = pd.DatetimeIndex(start=date-dt.timedelta(days=(period-1)), end=date, freq='D')
    new_df=pd.DataFrame(columns=['x','y','date','count','z','lat','lon'])
    for index,group in df.groupby(['lat','lon','countries']):
        group=expand_date_range(group,idx)
        new_df=pd.concat([new_df,group])
    del new_df['date']
    new_df.rename(columns={'index':'date'},inplace=True)
    return new_df


def analyze_data(stdin, stdout, date, period, count, graph):
    if not date:
        date=MAX_DATE
    else:
        #check for string
        date=dt.datetime.strptime(date,"%Y-%m-%d")
        date=MAX_DATE if date>MAX_DATE else date
    period=MIN_PERIOD if period<MIN_PERIOD else period
    tile_data=pd.read_csv(stdin,sep=',',parse_dates=['data'],keep_default_na=False)
    tile_data.rename(columns={'data':'date'},inplace=True)
    tile_data.drop_duplicates(inplace=True)
    tile_data=resample_missing_values(tile_data,date,period)
    tile_data=statistics(tile_data,period)
    high_outliers=tile_data[tile_data['Tscore']>=1.943]
    high_outliers.reset_index(inplace=True)
    high_outliers['values']=high_outliers.groupby('date')['abs_med'].apply(lambda x: (x-x.median())/x.median())
    high_outliers.set_index(['lat','lon','countries'],inplace=True)
    high_outliers.sort_values(['date','values'],ascending=False,inplace=True)
    trending_each_day=high_outliers.groupby('date')
    if graph:
        plot_graphs(tile_data,trending_each_day,date,date,count)
    else:
        solo_places,clustered_places=top_trending(trending_each_day.get_group(str(date.date())),count)
        export_to_csv(solo_places,clustered_places,high_outliers,stdout)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Determine and graph top 10 trending places')
    parser.add_argument('--date',default=None, help='The date to calculate trending places (min 3 days ago)')
    parser.add_argument('--period', type=int, default=7, help='Period of days to analyse trends (min 7)')
    parser.add_argument('--count', type=int,default=10, help='Give the trending country')
    parser.add_argument('--graph', action='store_true',default=False, help='Create the graphs of top n Trending places')

    stdin = sys.stdin if sys.version_info.major == 2 else sys.stdin.buffer
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer

    analyze_data(stdin,stdout,**parser.parse_args().__dict__)

















