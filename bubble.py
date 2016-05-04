import argparse
import itertools
import json
import collections
import datetime
import sys

import mercantile
import shapely.geometry


MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
MIN_ZOOM = 0
MAX_ZOOM = 19

count_weight = {
    0:0,1:0,2:0,3:0,4:0,5:0,6:0,7:0,8:0,9:0,10:0,11:0,12:1,13:1,14:1,15:2,16:4,17:8,18:16,19:32
}
cache_down = {}
cache_up = {}
cache_center = {}
cache_date = {}
cache_in_bound = {}


def get_down_tiles(x, y, z, target_zoom):
    assert z <= target_zoom, 'target zoom less than zoom %s <= %s' % (z, target_zoom)
    k = (x, y, z, target_zoom)
    if k not in cache_down:
        if z == target_zoom:
            result = [(x, y, z)]
        else:
            result = []
            for t in mercantile.children(x, y, z):
                result += get_down_tiles(t.x, t.y, t.z, target_zoom)
        cache_down[k] = tuple(result)
        return result
    return cache_down[k]


def get_up_tile(x, y, z, target_zoom):
    assert z >= target_zoom, 'target zoom more than zoom %s >= %s' % (z, target_zoom)
    k = (x, y, z, target_zoom)
    if k not in cache_up:
        if z == target_zoom:
            result = (x, y, z)
        else:
            t = mercantile.parent(x, y, z)
            result = get_up_tile(t.x, t.y, t.z, target_zoom)
        cache_up[k] = result
        return result
    return cache_up[k]


def get_date_precision(date, date_prec, date_prec_measure):
    if date not in cache_date:
        old_date = date
        if date_prec_measure == 'd':
            old_part = int(date[8:])
            new_part = old_part // date_prec * date_prec + (1 if old_part % date_prec else 0)
            date = '%s-%02d' % (date[:7], new_part)
        elif date_prec_measure == 'm':
            old_part = int(date[5:7])
            new_part = old_part // date_prec * date_prec + (1 if old_part % date_prec else 0)
            date = '%s-%02d-01' % (date[:4], new_part)
        elif date_prec_measure == 'y':
            old_part = int(date[:4])
            new_part = old_part // date_prec * date_prec + (1 if old_part % date_prec else 0)
            date = '%04d-01-01' % (new_part)
        else:
            raise TypeError('unknown date precision measure %s' % date_prec_measure)
        cache_date[old_date] = date
        return date
    return cache_date[date]


def calculate_center(x, y, z):
    k = (x, y, z)
    if k not in cache_center:
        bounds = mercantile.bounds(x, y, z)
        height = bounds.north - bounds.south
        width = bounds.east - bounds.west
        center = (bounds.north + height / 2, bounds.west + width / 2)
        cache_center[k] = center
        return center
    return cache_center[k]


def in_boundaries(k, lat, lon, boundary, west, south, east, north):
    if k not in cache_in_bound:
        in_bounds = lat < north and lat > south and lon > west and lon < east
        if in_bounds:
            in_bounds = boundary.contains(shapely.geometry.Point(lon, lat))
        cache_in_bound[k] = in_bounds
        return in_bounds
    return cache_in_bound[k]


FIELD_VALUES = (
    ('data', lambda k, date, count, *args, **kwargs: date, []),
    ('count', lambda k, date, count, *args, **kwargs: count, []),

    ('z', lambda k, date, count, z, x, y, *args, **kwargs: z, ['no_xyz']),
    ('x', lambda k, date, count, z, x, y, *args, **kwargs: x, ['no_xyz']),
    ('y', lambda k, date, count, z, x, y, *args, **kwargs: y, ['no_xyz']),

    ('lat', lambda k, date, count, z, x, y, lat, lon, *args, **kwargs: lat, ['no_latlon']),
    ('lon', lambda k, date, count, z, x, y, lat, lon, *args, **kwargs: lon, ['no_latlon']),

    ('per_day', lambda k, date, count, *args, **kwargs: count / kwargs['days'], ['no_per_day']),

    ('countries', lambda k, date, count, z, x, y, lat, lon, countries, *args, **kwargs: countries, ['no_countries']),
)


def flush_fields(stdout, date, count, z, x, y, lat, lon, countries, extra, headers=False, **kwargs):
    k = '%s/%s/%s' % (z, x, y)
    values = []
    for field, applier, filters in FIELD_VALUES:
        if any(kwargs.get(filter) for filter in filters):
            continue
        if headers:
            values.append(field)
        else:
            values.append(applier(k, date, count, z, x, y, lat, lon, countries, extra, **kwargs))

    if extra is not None:
        values.append(extra)
    stdout.write(('%s\n' % ','.join(str(value) for value in values)).encode())


def flush(stdout, tiles, min_count, max_count,  boundaries, **kwargs):
    for k, count in tiles.items():
        if min_count and count < min_count:
            continue
        if max_count and count > max_count:
            continue

        date, z, x, y, countries = k
        lat, lon = calculate_center(x, y, z)
        if boundaries is None:
            flush_fields(stdout, date, count, z, x, y, lat, lon, countries, None, **kwargs)
            continue
        for boundary, boundary_bounds, extra, hash in boundaries:
            cache_key = '%s/%s/%s' % (lat, lon, hash)
            if not in_boundaries(cache_key, lat, lon, boundary, *boundary_bounds):
                continue
            flush_fields(stdout, date, count, z, x, y, lat, lon, countries, extra, **kwargs)
    return collections.defaultdict(int)


def split(stdin, stdout, date_precision=None, per_day=False,
          boundaries=tuple(), boundary_buffer=None,
          date_from=None, date_to=None,
          min_count=None, max_count=None,
          min_zoom=None, max_zoom=None,
          min_subz=None, max_subz=None,
          extras=tuple(), extra_header=None, **kwargs):
    if not kwargs.get('no_per_day'):
        date_from_parsed = datetime.datetime.strptime(date_from, '%Y-%m-%d')
        date_to_parsed = datetime.datetime.strptime(date_to, '%Y-%m-%d')
        assert date_from_parsed
        assert date_to_parsed
        assert date_from_parsed < date_to_parsed
        kwargs['days'] = (date_to_parsed - date_from_parsed).days

    if not kwargs.get('no_header'):
        flush_fields(stdout, 'date', 'count', 'z', 'x', 'y', 'lat', 'lon', 'countries',
                     ','.join(extras) or None, headers=True,  **kwargs)

    boudaries_geom = []
    for boundary, extra in itertools.izip_longest(boundaries, extras):
        if isinstance(boundary, str):
            boundary = shapely.geometry.shape(json.load(open(boundary)))
        if boundary_buffer is not None:
            boundary = boundary.buffer(boundary_buffer)
        boudaries_geom.append((boundary, boundary.bounds, extra, id(boundary)))
    boudaries_geom = boudaries_geom or None

    if date_precision:
        date_prec = float(date_precision[:-1])
        date_prec_measure = date_precision[-1:]
    date_from = date_from or MIN_DATE
    date_to = date_to or MAX_DATE
    min_zoom = min_zoom or MIN_ZOOM
    max_zoom = max_zoom or MAX_ZOOM
    min_subz = min_subz or min_zoom
    max_subz = max_subz or max_zoom

    assert date_from <= date_to
    assert min_zoom <= max_zoom
    assert min_subz <= max_subz

    tiles = flush(stdout, {}, min_count, max_count, boudaries_geom, **kwargs)
    start = datetime.datetime.now()
    flush_date = None

    for line in stdin:
        print (line)
        date, z, x, y, count, lat, lon, countries = line.decode().strip().split(',')
        if not date_from <= date <= date_to:
            continue
        count = int(count)
        x = int(x)
        y = int(y)
        z = int(z)
        if not min_zoom <= z <= max_zoom:
            continue

        if date_precision is not None:
            date = get_date_precision(date, date_prec, date_prec_measure)

        if flush_date is None:
            start = datetime.datetime.now()
            flush_date = date

        if date != flush_date:
            sys.stderr.write('%s - %s\n' % (flush_date, datetime.datetime.now() - start))
            flush(stdout, tiles, min_count, max_count, boudaries_geom, **kwargs)
            flush_date = date
            start = datetime.datetime.now()

        if z < min_subz:
            print ('Getting down tiles for(xyz):'+str(x)+':'+str(y)+':'+str(z))
            for _x, _y, _z in get_down_tiles(x, y, z, min_subz):
                print ('\tDown tiles(xyz):'+str(_x)+':'+str(_y)+':'+str(_z))
                tiles[(date, _z, _x, _y, countries)] += count#*count_weight.get(z)
                print ('\tAdding all down tiles'+str(tiles[(date, _z, _x, _y, countries)]))
        if z > max_subz:
            print ('Getting up tiles for(xyz):'+str(x)+':'+str(y)+':'+str(z))
            _x, _y, _z = get_up_tile(x, y, z, max_subz)
            print ('\tUp tiles(xyz):'+str(_x)+':'+str(_y)+':'+str(_z))
            tiles[(date, _z, _x, _y, countries)] += count#*count_weight.get(z)
            print ('\tAdding up tile'+str(tiles[(date, _z, _x, _y, countries)]))
        if min_subz <= z <= max_subz:
            print ('Just sum (xyz):'+str(x)+':'+str(y)+':'+str(z))
            tiles[(date, z, x, y, countries)] += count#*count_weight.get(z)
            print ('\tAdding itslef'+str(tiles[(date, z, x, y, countries)]))

    sys.stderr.write('%s - %s\n' % (flush_date, datetime.datetime.now() - start))
    flush(stdout, tiles, min_count, max_count, boudaries_geom, **kwargs)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Agregate OSM access logs.')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to', default=None)
    parser.add_argument('--date_precision', default=None)
    parser.add_argument('--boundaries', action='append', default=[])
    parser.add_argument('--boundary_buffer', type=float, default=None)
    parser.add_argument('--min_zoom', type=int, default=None)
    parser.add_argument('--max_zoom', type=int, default=None)
    parser.add_argument('--min_subz', type=int, default=None)
    parser.add_argument('--max_subz', type=int, default=None)
    parser.add_argument('--min_count', type=int, default=None)
    parser.add_argument('--max_count', type=int, default=None)

    parser.add_argument('--no_header', action='store_true')
    parser.add_argument('--no_xyz', action='store_true')
    parser.add_argument('--no_latlon', action='store_true')
    parser.add_argument('--no_per_day', action='store_true')
    parser.add_argument('--no_countries', action='store_true')

    stdin = sys.stdin if sys.version_info.major == 2 else sys.stdin.buffer
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    split(stdin, stdout, **parser.parse_args().__dict__)
