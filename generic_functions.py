import json
import re

SCALE = 0.0277777777777778
origin_offset = []


def generate_map_dict(map_size, cell_size):
    format = 0.3
    origin = [0,0]
    size = map_size  # in tiles
    cell_size = cell_size  # in pixels

    generic_info = {
        "format": format,
        "resolution": {
            "map_origin": {
                    "x": origin[0],
                    "y": origin[1]
                },
            "map_size": {
                "x": size[0],
                "y": size[1]
            },
            "pixels_per_grid": cell_size
        }
    }

    map_dict = {
        **generic_info, 
        "line_of_sight": [],
        "objects_line_of_sight": [],
        "portals": [],
        "environment": {
            "baked_lighting": True,
            "ambient_light": "ffffffff"
        }, 
        "lights": [],
        "image": ""
        }
    
    return map_dict


def parse_map_data(file_name):
    with open(file_name, 'r', errors="ignore") as file:
        content = file.read()

    pattern = r'(?:map)({.*})'
    match = re.search(pattern, content)
    json_as_string = match.group(1)

    return json.loads(json_as_string)


def get_geometry_ids(map_data):
    layers = map_data["state"]["document"]["nodes"]
    layer_ids = layers.keys()

    geo_wall_ids = []
    geo_door_ids = []

    for layer_id in layer_ids:
        layer = layers[layer_id]
        type = layer["type"]

        if type == "GEOMETRY" and "geometryId" in layer:
            if layer["name"].startswith("Door"):
                geo_door_ids.append(layer["geometryId"])
            else:
                geo_wall_ids.append(layer["geometryId"])

    return {"walls": geo_wall_ids, "doors": geo_door_ids}

def extract_geometry(map_data, geometry_ids):
    geometry = map_data["data"]["geometry"]
    polygons = []
    polylines = []
    
    for geometry_id in geometry_ids:
        layer_geometry = geometry[geometry_id]

        polygons += layer_geometry["polygons"]
        polylines += layer_geometry["polylines"]

    return polygons, polylines


def update_origin_offset(coordinate):
    global origin_offset
    x = coordinate[0]
    y = coordinate[1]
    if not len(origin_offset):
        origin_offset = [x,y]
    else:
        origin_offset[0] = min(origin_offset[0], x)
        origin_offset[1] = min(origin_offset[1], y)

# TODO: combine convert_polygons and convert_polylines in single function
def convert_polygons(polygons):
    obstruction_lines = []

    # Don't know what the value of the outer container is
    for container in polygons:
        for polygon in container:
            coordinate_list = []
            for coordinate in polygon:
                update_origin_offset(coordinate)
                pair = {
                    "x": coordinate[0],
                    "y": coordinate[1],
                }
                coordinate_list.append(pair)
            obstruction_lines.append(coordinate_list)
    
    return obstruction_lines


def convert_polylines(polylines):
    obstruction_lines = []

    for polyline in polylines:
        coordinate_list = []
        for coordinate in polyline:
            update_origin_offset(coordinate)
            pair = {
                "x": coordinate[0],
                "y": coordinate[1],
            }
            coordinate_list.append(pair)
        obstruction_lines.append(coordinate_list)
    
    return obstruction_lines


def scale_and_offset_coordinates(obstruction_lines):
    for line in obstruction_lines:
        for coordinate in line:
            coordinate["x"] = (coordinate["x"] - origin_offset[0]) * SCALE
            coordinate["y"] = (coordinate["y"] - origin_offset[1]) * SCALE
    
    return obstruction_lines
