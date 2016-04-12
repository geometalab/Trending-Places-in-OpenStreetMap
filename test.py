import Top_trending as tt
import pandas as pd


date=None
period=7
count=10
graph=True
country=None
stdin='C:\\Work\\resampled2016-04-05.csv'
stdout=None
tile_data = pd.read_csv(stdin, sep=';', parse_dates=['date'], keep_default_na=False)
print (tile_data)
#tt.analyze_data(stdin, stdout, date,period,count,graph,country)

EMAIL='geometalab@gmail.com'
LINK='http://nominatim.openstreetmap.org/reverse.php?'
QUERY= 'lat=%f&lon=%f&zoom=10&format=xml&email='+EMAIL

fetch=LINK+QUERY % (51.289801107253936, -114.08203125)
