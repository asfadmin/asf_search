from ast import Lambda
from itertools import product
from typing import Dict, List
from asf_search import ASFSearchResults
import xml.etree.ElementTree as ETree

import os
import json
import shapely.wkt as WKT
import requests
import csv
from shapely.geometry import Polygon

# when this replaces SearchAPI change values to cached
API_URL = 'https://api.daac.asf.alaska.edu/services/search/param?'

def run_test_output_format(results: ASFSearchResults, output_type: str):
    product_list_str = ','.join([product.properties['fileID'] for product in results])
    expected = get_SearchAPI_Output(product_list_str, output_type)

    if output_type == 'csv':
        check_csv(results, expected)
    elif output_type == 'kml':
        check_kml(results, expected)
    elif output_type == 'metalink':
        results_metalink = results.metalink()
    elif output_type  in ['jsonlite', 'jsonlite2']:
        check_jsonLite(results, expected, output_type)

    pass

def check_kml(results: ASFSearchResults, expected_str: str):
    namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
    placemarks_path = ".//kml:Placemark"
    root = ETree.fromstring(expected_str)
    placemarks = root.findall(placemarks_path, namespaces)

    tags = ['name', 'description', 'styleUrl']
    actual_root = ETree.fromstring(''.join([line for line in results.kml()]))
    actual = actual_root.findall(placemarks_path, namespaces)

    placemarks.sort(key=lambda x: x[0].text)
    actual.sort(key=lambda x: x[0].text)
    for idx, element in enumerate(placemarks):
        for idy, field in enumerate(element):
            if field.tag.split('}')[-1] in tags:
                expected_el = str(ETree.tostring(field))
                actual_el = str(ETree.tostring(actual[idx][idy]))
                assert expected_el == actual_el
            elif field.tag.split('}')[-1] == 'Polygon':
                expected_coords = get_coordinates_from_kml(ETree.tostring(field))
                actual_coords = get_coordinates_from_kml(ETree.tostring(actual[idx][idy]))
                expected_polygon = Polygon(expected_coords)
                actual_polygon = Polygon(actual_coords)

                assert actual_polygon.equals(expected_polygon)


def get_coordinates_from_kml(data: str):
    namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}

    coords = []
    coords_lon_lat_path = ".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates"
    root = ETree.fromstring(data)
    
    coordinates_elements = root.findall(coords_lon_lat_path, namespaces)
    for lon_lat_z in coordinates_elements[0].text.split('\n'):
        if len(lon_lat_z.split(',')) == 3:
            lon, lat, _ = lon_lat_z.strip().split(',')
            coords.append([float(lon), float(lat)])

    return coords
    

def check_csv(results: ASFSearchResults, expected_str: str):
    expected = [product for product in csv.reader(expected_str.split('\n')) if product != []]
    actual = [prod for prod in csv.reader(results.csv()) if prod != []]
    
    assert expected.pop(0) == actual.pop(0)

    expected.sort(key=lambda product: product[0])
    
    for idx, product in enumerate(expected):
        assert actual[idx] == product
    pass

def check_jsonLite(results: ASFSearchResults, expected: str, output_type: str):
    expected = json.loads(expected)['results']
    sort_key = 'gn' if output_type == 'jsonlite2' else 'productID'
    expected.sort(key=lambda product: product[sort_key])

    if expected:
        if 'wkt' in expected[0].keys():
            wkt_key = 'wkt'
            wkt_unwrapped_key = 'wkt_unwrapped'
            jsonlite2 = False
        else:
            wkt_key = 'w'
            wkt_unwrapped_key = 'wu'
            jsonlite2 = True

    actual = json.loads(''.join(results.jsonlite2() if jsonlite2 else results.jsonlite()))['results']
    actual.sort(key=lambda product: product[sort_key])

    for idx, expected_product in enumerate(expected):
        wkt = expected_product.pop(wkt_key)
        wkt_unwrapped = expected_product.pop(wkt_unwrapped_key)
        
        for key in expected_product.keys():
            assert  actual[idx][key] == expected_product[key]
        
        assert WKT.loads(actual[idx][wkt_key]).equals(WKT.loads(wkt))
        assert WKT.loads(actual[idx][wkt_unwrapped_key]).equals(WKT.loads(wkt_unwrapped))

#
def get_SearchAPI_Output(product_list: List[str], output_type: str) -> List[Dict]:
    response = requests.get(API_URL, [('product_list', product_list), ('output', output_type)])
    response.raise_for_status()
    
    expected = response.text
    
    return expected