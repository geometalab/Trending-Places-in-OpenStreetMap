# Code attributions: Pavel Tyslacki
import argparse
import csv
import datetime
import gzip
import io
import itertools
import json
import lzma
import os
import pickle
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import lxml.etree
import mercantile
import overpass
import shapely.geometry
import shapely.wkt


LOGS_URL = 'http://planet.openstreetmap.org/tile_logs/'
MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
EXT = '.txt.xz'

COUNTRIES_QUERY = ('[out:csv(::id, "ISO3166-1", "ISO3166-1:alpha2")];'
                   '('
                   'relation["ISO3166-1"];'
                   'relation["ISO3166-1:alpha2"];'
                   ');'
                   'out tags;')
RELATION_QUERY = ('[out:csv(::id, "ISO3166-1", "ISO3166-1:alpha2")];'
                  '('
                  'relation(%s);'
                  ');'
                  'out tags;')

PREFETCH_GEOMETRY_LINK = 'http://polygons.openstreetmap.fr/?id=%s'
FETCH_GEOMETRY_LINK = 'http://polygons.openstreetmap.fr/get_wkt.py?id=%s&params=0'
MAX_FETCH_ATTEMPTS = [1, 3, 10, 30]
COUNTRIES_IDS_SKIP = (
    11980,
    1111111,
    1362232,
    1401925,
    5466491,
)

MIN_ZOOM = 0
MAX_ZOOM = 19
SPLIT_ZOOM = 8

MIN_INTERSECTION_AREA = 0.001
MIN_INTERSECTION_AREA_PER_PERIMETER = 0.01
MIN_GEOMETRY_AREA_PER_PERIMETER = 0.000005

DUMPS_CACHE_FOLDER = 'tile_logs'
COUNTRIES_GEOM_CACHE_FOLDER = 'countries'
GEOM_CACHE = 'cache_geoms.picle'
GROUPED_GEOM_CACHE = 'cache_grouped.picle'
GROUPED_GEOM_WITH_EMPTY_CACHE = 'cache_grouped_with_empty.picle'
SLICED_TO_TILES_GEOM_CACHE = 'cache_sliced_to_tiles.picle'
TILE_CACHE = 'cache_tile.json'


class Stat(object):

    def __init__(self):
        self.out = sys.stderr
        self.start = datetime.datetime.now()
        self.in_all = 0
        self.in_no_cached = 0
        self.in_child_cache = 0
        self.in_direct_cache = 0
        self.child_zoom_less = 0
        self.child_zoom_equal = 0
        self.filtered_bbox = 0
        self.filtered_geom = 0
        self.append_geom = 0

    def log_stats(self, msg, cache):
        cached_for_child = 0
        for cached_item in cache.values():
            if '|' not in cached_item:
                cached_for_child += 1
        self.log('%s - %s - ps: %s/%s - cc: %s/%s - zm: %s/%s - '
                 'fl: %s/%s - ap: %s - cs: %s/%s',
                 msg, datetime.datetime.now() - self.start,
                 self.in_all, self.in_no_cached,
                 self.in_child_cache, self.in_direct_cache,
                 self.child_zoom_less, self.child_zoom_equal,
                 self.filtered_bbox, self.filtered_geom,
                 self.append_geom,
                 cached_for_child, len(cache),
                 )

    def log(self, msg, *args):
        self.out.write('%s\n' % (msg % args))


def _fetch(link):
    attempt = 0
    while True:
        try:
            time.sleep(MAX_FETCH_ATTEMPTS[attempt])
            request = urllib.request.Request(link, headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            })
            return gzip.open(urllib.request.urlopen(request)).read().decode()
        except urllib.error.HTTPError:
            attempt += 1
            if attempt >= len(MAX_FETCH_ATTEMPTS):
                raise


def get_country_geom(osm_id, iso):
    prefetch_link = FETCH_GEOMETRY_LINK % osm_id
    link = FETCH_GEOMETRY_LINK % osm_id

    if not os.path.exists(COUNTRIES_GEOM_CACHE_FOLDER):
        os.mkdir(COUNTRIES_GEOM_CACHE_FOLDER)
    file_name_wkt = os.path.join(COUNTRIES_GEOM_CACHE_FOLDER,
                                 '%s-%s.wkt' % (iso, osm_id))
    file_name_geojson = os.path.join(COUNTRIES_GEOM_CACHE_FOLDER,
                                     '%s-%s.geojson' % (iso, osm_id))
    if os.path.exists(file_name_wkt):
        with open(file_name_wkt, 'r') as file:
            response = file.read()
        geom = shapely.wkt.loads(response)
    elif os.path.exists(file_name_geojson):
        with open(file_name_geojson, 'r') as file:
            response = file.read()
        geom = shapely.geometry.shape(json.loads(response))
    else:
        _fetch(prefetch_link)
        response = _fetch(link)
        if response.startswith('SRID=4326;'):
            response = response[len('SRID=4326;'):]
        geom = shapely.wkt.loads(response)
        with open(file_name_wkt, 'w') as file:
            file.write(response)

    return geom


def get_countries(rel=None, country=None, query=None):
    countries = {}
    if query:
        pass
    elif rel:
        query = RELATION_QUERY % rel
    else:
        query = COUNTRIES_QUERY
    response = overpass.API()._GetFromOverpass(query)
    reader = csv.reader(io.StringIO(response), delimiter='\t',)
    next(reader)
    for osm_id, iso3166_1, iso3166_1_alpha2 in reader:
        osm_id = int(osm_id)
        iso = iso3166_1 or iso3166_1_alpha2
        if not rel and not country and osm_id in COUNTRIES_IDS_SKIP:
            continue
        if not rel and (not iso or len(iso) != 2):
            continue
        if country and iso != country:
            continue
        if (osm_id, iso) in countries:
            continue
        Stat().log('%s-%s', iso, osm_id)
        geom = get_country_geom(osm_id, iso)
        countries[osm_id] = (iso, geom, geom.bounds)

    return countries


def _clear_xml_element(element):
    element.clear()
    for ancestor in element.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


def get_date_from_link(link):
    return link[:-len(EXT)][-len(MIN_DATE):]


def get_tile_usage_dump_links(date_from=None, date_to=None):
    date_from = date_from or MIN_DATE
    date_to = date_to or MAX_DATE
    links = set()

    response = urllib.request.urlopen(LOGS_URL)
    for action, element in lxml.etree.iterparse(response, tag='a', html=True):
        link = element.attrib['href']
        _clear_xml_element(element)
        if not link.endswith(EXT):
            continue
        if not date_from <= get_date_from_link(link) <= date_to:
            continue
        links.add(urllib.parse.urljoin(LOGS_URL, link))

    return sorted(links)


def get_tile_usage_dump(link):
    dump_cache = os.path.join(DUMPS_CACHE_FOLDER,
                              link[-len('tiles-YYYY-MM-DD.txt.xz'):])
    if os.path.exists(dump_cache):
        return io.BytesIO(open(dump_cache, 'rb').read())
    return urllib.request.urlopen(link)


def detect_country(b, x, y, z, part_zoom, tiled_countries, all_countries, stat):
    twest, tsouth, teast, tnorth = b
    tgeom = shapely.geometry.box(twest, tsouth, teast, tnorth)
    result = None

    if z < part_zoom:
        countries = all_countries
    else:
        delta_zooms = z - part_zoom
        delta = 2 ** delta_zooms
        px = x // delta
        py = y // delta
        countries = tiled_countries['%s/%s/%s' % (part_zoom, px, py)]

    for iso, boundary, outer_box in countries:
        owest, osouth, oeast, onorth = outer_box
        if not (twest <= oeast and teast >= owest and
                tnorth >= osouth and tsouth <= onorth):
            stat.filtered_bbox += 1
            continue
        if not boundary.intersects(tgeom):
            stat.filtered_geom += 1
            continue
        if result is None:
            result = {iso}
        else:
            result.add(iso)
        stat.append_geom += 1
    return result and '|'.join(sorted(result)) or '??'


def detect_country_with_cache(k, b, x, y, z,
                              part_zoom, tiled_countries, all_countries,
                              min_cache_zoom, cache, stat):
    stat.in_all += 1
    if k in cache:
        stat.in_direct_cache += 1
        return cache[k]

    for pz in range(min_cache_zoom, z):
        delta_zooms = z - pz
        delta = 2 ** delta_zooms
        px = x // delta
        py = y // delta
        ck = '%s/%s/%s' % (pz, px, py)
        potential_cc = False
        if ck in cache:
            country = cache[ck]
            potential_cc = True
        else:
            stat.in_no_cached += 1
            country = detect_country(
                b, px, py, pz, part_zoom, tiled_countries, all_countries, stat)
            cache[k] = country

        if pz < z and '|' not in country:
            stat.child_zoom_less += 1
            if potential_cc:
                stat.in_child_cache += 1
            return country

    stat.in_no_cached += 1
    stat.child_zoom_equal += 1
    country = detect_country(
        b, x, y, z, part_zoom, tiled_countries, all_countries, stat)
    cache[k] = country
    return country


def process_item(out, min_cache_zoom, cache, link,
                 part_zoom, tiled_countries, all_countries,
                 min_zoom, max_zoom, skip_empty_tiles):
    stat = Stat()
    date = get_date_from_link(link)

    for line in lzma.LZMAFile(get_tile_usage_dump(link)):
        path, count = line.decode().strip().split()
        z, x, y = path.split('/')

        x = int(x)
        y = int(y)
        z = int(z)

        if min_zoom is not None and z < min_zoom:
            continue
        if max_zoom is not None and z > max_zoom:
            continue

        twest, tsouth, teast, tnorth = b = mercantile.bounds(x, y, z)
        country = detect_country_with_cache(
            path, b, x, y, z, part_zoom, tiled_countries, all_countries,
            min_cache_zoom, cache, stat)

        if skip_empty_tiles and country == '??':
            continue

        lat = tnorth + (tnorth - tsouth) / 2
        lon = twest + (teast - twest) / 2

        out.write(('%s,%s,%s,%s,%s,%s,%s,%s\n' % (
            date, z, x, y, count, lat, lon, country)).encode())
    stat.log_stats(date, cache)


def create_cache(part_zoom, countries, splited_countries, min_cache_zoom):
    stat = Stat()

    cache = {}
    if min_cache_zoom:
        stat.log_stats('cache (%s)' % min_cache_zoom, cache)
        return min_cache_zoom, cache

    min_cache_zoom = MIN_ZOOM
    for z in range(MAX_ZOOM + 1):
        for x in range(2 ** z):
            for y in range(2 ** z):
                k = '%s/%s/%s' % (z, x, y)
                b = mercantile.bounds(x, y, z)
                country = detect_country_with_cache(
                    k, b, x, y, z, part_zoom, countries, splited_countries,
                    z, cache, stat)
                if '|' not in country:
                    min_cache_zoom = z
        if min_cache_zoom > 0:
            break
    stat.log_stats('cache (%s)' % min_cache_zoom, cache)
    return min_cache_zoom, cache


def add_no_country_items(grouped_countries, tiled_countries):
    no_country_geoms = {}
    for tile, iso_geoms in tiled_countries.items():
        z, x, y = tile.split('/')
        group_divider = max(2 ** int(z) // 32, 1)
        group_key = (int(x) // group_divider, int(y) // group_divider)
        for iso, geom, _ in iso_geoms:
            if iso != '??':
                continue
            if group_key not in no_country_geoms:
                no_country_geoms[group_key] = geom
            else:
                no_country_geoms[group_key] = no_country_geoms[group_key].union(geom)
    return grouped_countries + tuple(('??', geom, geom.bounds)
                                     for geom in no_country_geoms.values())


def slice_geoms_to_tiles(grouped_countries):
    tiles = {}
    z = SPLIT_ZOOM
    for x in range(2 ** z):
        for y in range(2 ** z):
            start = datetime.datetime.utcnow()
            twest, tsouth, teast, tnorth = mercantile.bounds(x, y, z)
            bound = shapely.geometry.box(twest, tsouth, teast, tnorth)
            no_country_geom = shapely.geometry.box(twest, tsouth, teast, tnorth)
            parts = []
            for iso, geom, _ in grouped_countries:
                if not bound.intersects(geom):
                    continue
                geom_part = bound.intersection(geom)
                no_country_geom = no_country_geom.difference(geom_part)
                parts.append((iso, geom_part))

            if not no_country_geom.buffer(0).is_empty:
                parts.append(('??', no_country_geom))

            time_spent = (datetime.datetime.utcnow() - start).total_seconds()
            Stat().log('polygons in %s/%s/%s: %s - %s%s', z, x, y,
                       len(parts), '|'.join(iso for iso, _ in parts),
                       '' if time_spent < 1 else (' (%s sec.)' % time_spent))
            tiles['%s/%s/%s' % (z, x, y)] = tuple((iso, geom, geom.bounds)
                                                  for iso, geom in parts)
    return tiles


def group_geoms(countries):
    grouped_countries = {}
    for iso, geom, bbox in countries.values():
        geom = geom.buffer(0)
        if iso not in grouped_countries:
            grouped_countries[iso] = geom
        else:
            grouped_countries[iso] = grouped_countries[iso].union(geom)

    overlapped = []
    for iso_geom_1, iso_geom_2 in itertools.combinations(grouped_countries.items(), 2):
        iso_1, geom_1 = iso_geom_1
        iso_2, geom_2 = iso_geom_2
        west_1, south_1, east_1, north_1 = geom_1.bounds
        west_2, south_2, east_2, north_2 = geom_2.bounds
        if not (west_1 <= east_2 and east_1 >= west_2 and
                north_1 >= south_2 and south_1 <= north_2):
            continue
        if not geom_1.intersects(geom_2):
            continue
        intersection = geom_1.intersection(geom_2)
        if not intersection.area or not intersection.length:
            continue
        area_per_perimeter = intersection.area / intersection.length
        if (intersection.area < MIN_INTERSECTION_AREA or
                area_per_perimeter < MIN_INTERSECTION_AREA_PER_PERIMETER):
            continue
        overlapped.append([iso_1, iso_2])
        Stat().log('intersects %s and %s', iso_1, iso_2)

    # only 2 geometries overlapping processed,
    # 3 and more ignored because not found for enough big intersection
    grouped_countries_update = {}
    for iso_1, iso_2 in overlapped:
        geom_1 = grouped_countries[iso_1]
        geom_2 = grouped_countries[iso_2]
        iso_1_2 = '+'.join(sorted([iso_1, iso_2]))
        grouped_countries_update[iso_1_2] = geom_1.intersection(geom_2)

        for iso, geom, geom_other in ((iso_1, geom_1, geom_2), (iso_2, geom_2, geom_1)):
            geom = grouped_countries_update.get(iso, geom)
            if geom is None:
                continue
            geom = geom.difference(geom_other)
            if (geom.is_empty or not geom.area or not geom.length or
                    geom.area / geom.length < MIN_GEOMETRY_AREA_PER_PERIMETER):
                geom = None
            grouped_countries_update[iso] = geom

    grouped_countries.update(grouped_countries_update)

    return tuple((iso, geom, geom.bounds)
                 for iso, geom in grouped_countries.items()
                 if geom and not geom.is_empty)


def _cached_op(op, *args, title=None, cache=None, loader=pickle, block=True):
    if cache and os.path.exists(cache):
        with open(cache, 'rb' if block else 'r') as cache_file:
            result = loader.load(cache_file)
    else:
        result = op(*args)
        if cache:
            with open(cache, 'wb' if block else 'w') as cache_file:
                loader.dump(result, cache_file)
    if title:
        Stat().log('%s: %s', title, len(result))
    return result


def process_all(out, date_from=None, date_to=None,
                min_zoom=None, max_zoom=None,
                rel=None, country=None, min_cache_zoom=None):
    use_cache = not rel and not country
    full_countries = _cached_op(
        get_countries, rel, country,
        title='total countries', cache=use_cache and GEOM_CACHE)
    grouped_countries = _cached_op(
        group_geoms, full_countries,
        title='grouped countries', cache=use_cache and GROUPED_GEOM_CACHE)
    tiled_countries = _cached_op(
        slice_geoms_to_tiles, grouped_countries,
        title='total parts', cache=use_cache and SLICED_TO_TILES_GEOM_CACHE)
    grouped_countries = _cached_op(
        add_no_country_items, grouped_countries, tiled_countries,
        title='grouped with empty', cache=use_cache and GROUPED_GEOM_WITH_EMPTY_CACHE)
    min_cache_zoom, cache = _cached_op(
        create_cache, SPLIT_ZOOM, tiled_countries, grouped_countries, min_cache_zoom,
        cache=use_cache and TILE_CACHE, loader=json, block=False)

    for link in get_tile_usage_dump_links(date_from, date_to):
        process_item(out, min_cache_zoom, cache, link,
                     SPLIT_ZOOM, tiled_countries, grouped_countries,
                     min_zoom, max_zoom, rel or country)
        if use_cache:
            with open(TILE_CACHE, 'w') as tile_cache_file:
                json.dump([min_cache_zoom, cache], tile_cache_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch and concat OSM tiles access logs.')
    parser.add_argument('--date_from', default=None, help='filter from date (min 2014-01-01)')
    parser.add_argument('--date_to', default=None, help='filter to date (max today)')
    parser.add_argument('--min_zoom', type=int, default=None, help='filter from zoom (min 0)')
    parser.add_argument('--max_zoom', type=int, default=None, help='filter to zoom (max 19)')
    parser.add_argument('--rel', type=int, default=None, help='filter by OSM relation id geometry')
    parser.add_argument('--country', default=None, help='filter by country ISO3166 alpha 2 code OSM geometry')
    parser.add_argument('--min_cache_zoom', type=int, default=None)
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    process_all(stdout, **parser.parse_args().__dict__)
