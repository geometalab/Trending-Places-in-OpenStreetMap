# Trending-Places-in-OpenStreetMap
[![Stories in Ready](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=ready&title=Ready)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)
[![Stories in In Progress](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=In Progress&title=In Progress)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)

This is an experimental bot to calculate the Trending places in OSM.

## Execution with Docker

>*Prerequsite:* docker

```shell
docker build -t trendingplaces:v1 .
```
```shell
docker run -v $(pwd):/src trendingplaces:v1
```
## Execution manually

>*Prerequsite:* Python 3 and Virtual Environment

<p>Set up a python virtual environment and start with ```pip install -r requirements.txt```<br>
  Matplotlib and lxml might need additional dependencies which can be installed by:
```shell
apt-get build-dep python-matplotlib
``` 
```shell
apt-get build-dep python3-lxml
```  

### Running the code
Step 1 and 2 are based on previous work done by Lucas Martinelli and Pavel Tyslacki on <a href="https://github.com/lukasmartinelli/map-trends">map-trends</a>.
- *STEP 1:* Fetch the Tile Logs with ```python3 fetch2.py --date_from=(date_to-7 days back) --date_to=(today-2) >Trends.csv:```
    - Fetches the tile logs for 7 days from http://planet.openstreetmap.org/tile_logs/
    - Extracts them
    - Finds lat/lon based on the tile center and groups it into the respective country to which it belongs
- *STEP 2:* ```cat Trends.csv|python3 bubble.py --date_precision=1d --min_zoom=10
 --max_zoom=19 --min_subz=10 --max_subz=10 --no_per_day>Zoom10Tiles.csv ```
    - The max/min_zoom specify the output zoom level i.e. all views aggregated here. 10 is selected as it is the optimal level to view cities
    - The min/max_subz specify the input levels to aggregate views. 
    - Levels 1-10 are ignore as they are considered insignificant, with almost 100% views everyday.
- *STEP 3:*  ```cat Zoom10Tiles.csv | python Top_trending.py --graph```
   - *Input:* --date (Default 2 days ago unless specified)  
     --limit (default 10 for top 10 trending places)  
     --period (default 7 for the sampling interval)  
     --country(to specify a country to deduce the trending places in)  
     --graph(to generate a .png file showing the trending places views)  
   - *The output:* trending_places.png (Optional)  
                   trending_places.db (containing the lat/lon/count etc)  
- *STEP 4:* ``` python Trending_Bot.py```
  Before running this twitter bot, you will need to set up your twitter developer account and **add in the consumer and token access keys in the config file**! A sample format is available on github.


For further explaination, please read:
See http://geometalab.github.io/Trending-Places-in-OpenStreetMap
