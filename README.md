# Trending-Places-in-OpenStreetMap
[![Stories in Ready](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=ready&title=Ready)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)
[![Stories in In Progress](https://badge.waffle.io/geometalab/Trending-Places-in-OpenStreetMap.png?label=In Progress&title=In Progress)](https://waffle.io/geometalab/Trending-Places-in-OpenStreetMap)

This is an experimental bot to calculate the Trending places in OSM.

Prereq: docker

## Execution
```shell
docker build -t trendingplaces:v1 .
```
```shell
docker run -v $(pwd):/src trendingplaces:v1
```

For further explaination, please read:
See http://geometalab.github.io/Trending-Places-in-OpenStreetMap
