# Trending-Places-in-OpenStreetMap
[![Stories in Ready](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=ready&title=Ready)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)
[![Stories in In Progress](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=In Progress&title=In Progress)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)

This is an experimental bot to calculate the Trending places in OSM.

Note: The first execution might take a few hours, but it shold become faster thereafter.

## Execution with Docker

>*Prerequsite:* docker

Clone this repository and make it your active folder.  
If you want the twitter bot to Tweet a status, register as a developer on twitter and obtain the 4 keys to authenticate your twitter bot. The four variables required are mentioned in the sample config file.
These need to be set as environment variables system and/or in your docker container.
Example: (You need to repeat this for all four or directly input it in the docker container with -e) 

 ```shell
CONSUMER_KEY="somevaluehere"
 ```
Then run the following:

```shell
docker build -t trendingplaces:v1 .
```
To run the main program:

```shell
docker run -e CONSUMER_KEY -e CONSUMER_SECRET -e ACCESS_TOKEN -e ACCESS_TOKEN_SECRET trendingplaces:v1 ./main.sh
```
OR   
To set it up with a cron job that executes once every day:
```shell
docker run -e CONSUMER_KEY -e CONSUMER_SECRET -e ACCESS_TOKEN -e ACCESS_TOKEN_SECRET trendingplaces:v1
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
- *STEP 1:* Fetch the Tile Logs with ```python3 Fetch2.py --date_from=(date_to-7 days back) --date_to=(today-2) >Trends.csv:```
    - Fetches the tile logs for 7 days from http://planet.openstreetmap.org/tile_logs/
    - Extracts them
    - Finds lat/lon based on the tile center and groups it into the respective country to which it belongs
- *STEP 2:* ```cat Trends.csv|python3 Bubble.py --date_precision=1d --min_zoom=10
 --max_zoom=19 --min_subz=10 --max_subz=10 --no_per_day>Zoom10Tiles.csv ```
    - The max/min_zoom specify the output zoom level i.e. all views aggregated here. 10 is selected as it is the optimal level to view cities
    - The min/max_subz specify the input levels to aggregate views. 
    - Levels 1-10 are ignore as they are considered insignificant, with almost 100% views everyday.
- *STEP 3:*  ```cat Zoom10Tiles.csv | python3 Top_trending.py --graph```
   - *Input:* --date (Default 2 days ago unless specified)  
     --limit (default 10 for top 10 trending places)  
     --period (default 7 for the sampling interval)  
     --country(to specify a country to deduce the trending places in)  
     --graph(to generate a .png file showing the trending places views)  
   - *The output:* trending_places.png (Optional)  
                   trending_places.db (containing the lat/lon/count etc)  
- *STEP 4:* ``` python3 Trending_Bot.py```
  Before running this twitter bot, you will need to set up your twitter developer account and **add in the consumer and token access keys as environment variables in your system before this**! A sample format is available on github.


For further explaination, please read:
See http://geometalab.github.io/Trending-Places-in-OpenStreetMap
