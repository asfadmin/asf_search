from ast import Tuple
from datetime import datetime
from typing import Any, Dict
from asf_search.ASFSearchOptions import ASFSearchOptions, validators
from asf_search.constants import DEFAULT_PROVIDER, CMR_PAGE_SIZE
# from asf_search.search.search import fix_date
import dateparser
from .field_map import field_map

from WKTUtils import Input

from warnings import warn

def translate_opts(opts: ASFSearchOptions) -> list:
    # Need to add params which ASFSearchOptions cant support (like temporal),
    # so use a dict to avoid the validate_params logic:
    dict_opts = dict(opts)
    # Dict only copies CMR params. Copy provider over too:
    dict_opts['provider'] = opts.provider

    # Special case to unravel WKT field a little for compatibility
    if "intersectsWith" in dict_opts:
        cmr_wkt = Input.parse_wkt_util(dict_opts["intersectsWith"])
        dict_opts.pop("intersectsWith", None)
        # Add it to the dict w/ how cmr expects:
        (shapeType, shape) = cmr_wkt.split(':')
        dict_opts[shapeType] = shape

    # If you need to use the temporal key:
    if any(key in dict_opts for key in ['start', 'end', 'season']):
        start = dict_opts["start"] if "start" in dict_opts else ""
        end = dict_opts["end"] if "end" in dict_opts else ""
        season = ','.join(str(x) for x in dict_opts["season"]) if "season" in dict_opts else ""

        dict_opts['temporal'] = f'{start},{end},{season}'
        dict_opts.pop("start", None)
        dict_opts.pop("end", None)
        dict_opts.pop("season", None)

    # convert the above parameters to a list of key/value tuples
    cmr_opts = []
    for (key, val) in dict_opts.items():
        if isinstance(val, list):
            for x in val:
                if key in ['granule_list', 'product_list']:
                    for y in x.split(','):
                        cmr_opts.append((key, y))
                else:
                    cmr_opts.append((key, x))
        else:
            cmr_opts.append((key, val))

    # translate the above tuples to CMR key/values
    for i, opt in enumerate(cmr_opts):
        cmr_opts[i] = field_map[opt[0]]['key'], field_map[opt[0]]['fmt'].format(opt[1])
    
    cmr_opts.append(('page_size', CMR_PAGE_SIZE))

    return cmr_opts


def translate_product(item: dict) -> dict:
    coordinates = item['umm']['SpatialExtent']['HorizontalSpatialDomain']['Geometry']['GPolygons'][0]['Boundary']['Points']
    coordinates = [[c['Longitude'], c['Latitude']] for c in coordinates]
    geometry = {'coordinates': [coordinates], 'type': 'Polygon'}

    umm = item['umm']

    properties = {
        'beamModeType': get(umm, 'AdditionalAttributes', ('Name', 'BEAM_MODE_TYPE'), 'Values', 0),
        'browse': get(umm, 'RelatedUrls', ('Type', 'GET RELATED VISUALIZATION'), 'URL'),
        'bytes': cast(int, try_strip_trailing_zero(get(umm, 'AdditionalAttributes', ('Name', 'BYTES'), 'Values', 0))),
        'centerLat': cast(float, get(umm, 'AdditionalAttributes', ('Name', 'CENTER_LAT'), 'Values', 0)),
        'centerLon': cast(float, get(umm, 'AdditionalAttributes', ('Name', 'CENTER_LON'), 'Values', 0)),
        'faradayRotation': cast(float, get(umm, 'AdditionalAttributes', ('Name', 'FARADAY_ROTATION'), 'Values', 0)),
        'fileID': get(umm, 'GranuleUR'),
        'flightDirection': get(umm, 'AdditionalAttributes', ('Name', 'FLIGHT_DIRECTION'), 'Values', 0),
        'groupID': get(umm, 'AdditionalAttributes', ('Name', 'GROUP_ID'), 'Values', 0),
        'granuleType': get(umm, 'AdditionalAttributes', ('Name', 'GRANULE_TYPE'), 'Values', 0),
        'insarStackId': get(umm, 'AdditionalAttributes', ('Name', 'INSAR_STACK_ID'), 'Values', 0),
        'md5sum': get(umm, 'AdditionalAttributes', ('Name', 'MD5SUM'), 'Values', 0),
        'offNadirAngle': cast(float, get(umm, 'AdditionalAttributes', ('Name', 'OFF_NADIR_ANGLE'), 'Values', 0)),
        'orbit': cast(int, get(umm, 'OrbitCalculatedSpatialDomains', 0, 'OrbitNumber')),
        'pathNumber': cast(int, get(umm, 'AdditionalAttributes', ('Name', 'PATH_NUMBER'), 'Values', 0)),
        'platform': get(umm, 'AdditionalAttributes', ('Name', 'ASF_PLATFORM'), 'Values', 0),
        'pointingAngle': cast(float, get(umm, 'AdditionalAttributes', ('Name', 'POINTING_ANGLE'), 'Values', 0)),
        'polarization': get(umm, 'AdditionalAttributes', ('Name', 'POLARIZATION'), 'Values', 0),
        'processingDate': get(umm, 'DataGranule', 'ProductionDateTime'),
        'processingLevel': get(umm, 'AdditionalAttributes', ('Name', 'PROCESSING_TYPE'), 'Values', 0),
        'sceneName': get(umm, 'DataGranule', 'Identifiers', ('IdentifierType', 'ProducerGranuleId'), 'Identifier'),
        'sensor': get(umm, 'Platforms', 0, 'Instruments', 0, 'ShortName'),
        'startTime': get(umm, 'TemporalExtent', 'RangeDateTime', 'BeginningDateTime'),
        'stopTime': get(umm, 'TemporalExtent', 'RangeDateTime', 'EndingDateTime'),
        'url': get(umm, 'RelatedUrls', ('Type', 'GET DATA'), 'URL')
    }

    for key in ['temporalBaseline', 'perpendicularBaseline']:
        if "properties" in item and key in item['properties']:
            properties[key] = item['properties'][key]

    stateVectors = {}
    positions = {}
    velocities = {}
    positions['prePosition'], positions['prePositionTime'] = cast(get_state_vector, get(umm, 'AdditionalAttributes', ('Name', 'SV_POSITION_PRE'), 'Values', 0))
    positions['postPosition'], positions['postPositionTime'] = cast(get_state_vector, get(umm, 'AdditionalAttributes', ('Name', 'SV_POSITION_POST'), 'Values', 0))
    velocities['preVelocity'], velocities['preVelocityTime'] = cast(get_state_vector, get(umm, 'AdditionalAttributes', ('Name', 'SV_VELOCITY_PRE'), 'Values', 0))
    velocities['postVelocity'], velocities['postVelocityTime'] = cast(get_state_vector, get(umm, 'AdditionalAttributes', ('Name', 'SV_VELOCITY_POST'), 'Values', 0))
    ascendingNodeTime = get(umm, 'AdditionalAttributes', ('Name', 'ASC_NODE_TIME'), 'Values', 0)


    stateVectors = {
        'positions': positions,
        'velocities': velocities
    }

    insarBaseline = cast(float, get(umm, 'AdditionalAttributes', ('Name', 'INSAR_BASELINE'), 'Values', 0))
    
    baseline = {}
    if None not in stateVectors['positions'].values() and len(stateVectors.items()) > 0:
        baseline['stateVectors'] = stateVectors
        baseline['ascendingNodeTime'] = ascendingNodeTime
    elif insarBaseline is not None:
        baseline['insarBaseline'] = insarBaseline
    else:
        baseline = None


    properties['fileName'] = properties['url'].split('/')[-1]

    asf_frame_platforms = ['Sentinel-1A', 'Sentinel-1B', 'ALOS']
    if properties['platform'] in asf_frame_platforms:
        properties['frameNumber'] = get(umm, 'AdditionalAttributes', ('Name', 'FRAME_NUMBER'), 'Values', 0)
    else:
        properties['frameNumber'] = get(umm, 'AdditionalAttributes', ('Name', 'CENTER_ESA_FRAME'), 'Values', 0)

    return {'geometry': geometry, 'properties': properties, 'type': 'Feature', 'baseline': baseline}


def cast(f, v):
    try:
        return f(v)
    except TypeError:
        return None


def get(item: dict, *args):
    for key in args:
        if isinstance(key, int):
            item = item[key] if key < len(item) else None
        elif isinstance(key, tuple):
            (a, b) = key
            found = False
            for child in item:
                if get(child, a) == b:
                    item = child
                    found = True
                    break
            if not found:
                return None
        else:
            item = item.get(key)
        if item is None:
            return None
    if item in [None, 'NA', 'N/A', '']:
        item = None
    return item

def get_state_vector(state_vector: str):
    if state_vector is None:
        return None, None
    
    return list(map(float, state_vector.split(',')[:3])), state_vector.split(',')[-1]

def try_strip_trailing_zero(value: str):
    if value != None:
        return value.rstrip('.0')
    
    return value

def fix_date(fixed_params: Dict[str, Any]):
    if 'start' in fixed_params or 'end' in fixed_params or 'season' in fixed_params:
        fixed_params["start"] = fixed_params["start"] if "start" in fixed_params else ""
        fixed_params["end"] = fixed_params["end"] if "end" in fixed_params else ""
        fixed_params["season"] = ','.join(str(x) for x in fixed_params['season']) if "season" in fixed_params else ""

        fixed_params['temporal'] = f'{fixed_params["start"]},{fixed_params["end"]},{fixed_params["season"]}'

        # And a little cleanup
        fixed_params.pop('start', None)
        fixed_params.pop('end', None)
        fixed_params.pop('season', None)
        
    return fixed_params
