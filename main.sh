#!/bin/bash
# Generates the Top 10 trending places on OSM (with a 2 day lag)

tile_log_diff="2"
date_diff="7"

date_to=$(date "--date=${dataset_date} -${tile_log_diff} day" +%Y-%m-%d)
date_from=$(date "--date=${date_to} -${date_diff} day+1 day" +%Y-%m-%d)

python3 Fetch2.py --date_from=$date_from --date_to=$date_to >Trends.csv &&
cat Trends.csv|python3 Bubble.py --date_precision=1d --min_zoom=14 --max_zoom=19 --min_subz=14 --max_subz=14 --no_per_day>Zoom10Tiles.csv &&
cat Zoom10Tiles.csv | python3 Top_Trending.py --graph &&
python3 Trending_Bot.py
