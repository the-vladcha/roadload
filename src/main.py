import io
import json

import numpy as np
import folium
from PIL import Image
from folium import Map
from pyproj import Transformer, Geod
from shapely import LineString
import geopandas as gpd

TRANSFORMER: Transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326")


def _load_data() -> dict:
    with open('./data.json', encoding='utf-8') as file:
        return json.load(file)


def _get_load_color(load: int) -> str:
    if load is None:
        return '#6c6c6c'
    if 0 <= load <= 2:
        return '#0CBE00'
    if 3 <= load <= 6:
        return '#FFDD1C'
    if 7 <= load <= 9:
        return '#E20000'
    return '#760000'


def _init_map(data: dict) -> Map:
    center: tuple = (np.mean([node['geometry']['center'][0] for node in data['graph']['nodes']]),
                     np.mean([node['geometry']['center'][1] for node in data['graph']['nodes']]))
    m: Map = folium.Map(
        list(TRANSFORMER.transform(*center)),
        width=data['image']['width'],
        height=data['image']['height'],
        tiles='cartodbpositron',
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False,
        attributionControl=False,
    )
    line: gpd.GeoDataFrame = gpd.GeoDataFrame(
        index=[0],
        crs='EPSG:4326',
        geometry=[
            LineString([TRANSFORMER.transform(*node['geometry']['center'])[::-1] for node in data['graph']['nodes']])
        ])
    folium.FitBounds([[line.bounds.miny[0], line.bounds.minx[0]], [line.bounds.maxy[0], line.bounds.maxx[0]]]).add_to(m)
    return m


def _draw_nodes(data: dict, m: Map) -> None:
    for node in data['graph']['nodes']:
        folium.Circle(TRANSFORMER.transform(*node['geometry']['center']), radius=node['geometry']['radius'],
                      color='#000', fill=True, fill_color='#000', dash_array='10').add_to(m)


def _create_arrow(loc: list, m: Map, scale: float) -> None:
    pairs: list = [(loc[idx], loc[idx - 1]) for idx, val in enumerate(loc) if idx != 0]
    geodesic: Geod = Geod(ellps='WGS84')
    rotations: list = [geodesic.inv(pair[0][1], pair[0][0], pair[1][1], pair[1][0])[0] + 90 for pair in pairs]
    for pair, rot in zip(pairs, rotations):
        folium.RegularPolygonMarker(location=pair[0], color='red',
                                    number_of_sides=3, rotation=rot, radius=int(1 * scale)).add_to(m)


def _draw_links(data: dict, m: Map) -> None:
    loads: dict = {load['link_id']: load['load'] for load in data['loads']}
    scale: float = data['image']['width'] / 300
    if scale < 1:
        scale = 1
    for link in data['graph']['links']:
        loc: list = [TRANSFORMER.transform(*coordinate) for coordinate in link['geometry']['coordinates']]
        folium.PolyLine(loc, color=_get_load_color(loads.get(link['id'])), weight=3 * scale).add_to(m)
        _create_arrow(loc, m, scale)


def _generate_image(m: Map) -> None:
    img_bytes: io.BytesIO = io.BytesIO(m._to_png(5))
    img: Image = Image.open(img_bytes)
    img.save('./result_data/result.png')
    with open('./result_data/result.json', 'w', encoding='utf-8') as file:
        json.dump({'image': str(img_bytes.getvalue())}, file, indent=4, ensure_ascii=False)


def main() -> None:
    data: dict = _load_data()
    m: Map = _init_map(data)
    _draw_nodes(data, m)
    _draw_links(data, m)
    _generate_image(m)


if __name__ == '__main__':
    main()
