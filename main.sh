#!/bin/bash
# Generates the Top 10 trending places on OSM (with a 2 day lag)

tile_log_diff="2"
date_diff="7"

date_to=$(date "--date=${dataset_date} -${tile_log_diff} day" +%Y-%m-%d)
date_from=$(date "--date=${dataset_date} -${date_diff} day-1 day" +%Y-%m-%d)

python3 fetch2.py --date_from=$date_from --date_to=$date_to >Trends.csv
cat Trends.csv|python3 bubble.py --date_precision=1d --min_zoom=10 --max_zoom=19 --min_subz=10 --max_subz=10 --no_per_day>Zoom10Tiles.csv
cat Zoom10Tiles.csv | python3 Top_trending.py --graph
python3 Trending_Bot.py

