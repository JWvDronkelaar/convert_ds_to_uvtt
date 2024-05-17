
import base64
import argparse
import json
import math
import re

SCALE = 0.0277777777777778
origin_offset = []

# region generic functions

def generate_map_dict(map_size, cell_size):
    format = 0.3
    origin = [0,0]
    size = map_size 
    cell_size = cell_size

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
        layer_name = layer["name"]

        if type == "GEOMETRY":
            if layer_name == "Door geometry":
                geo_door_ids.append(layer["geometryId"])
            elif layer_name != "Stairs geometry":
                geo_wall_ids.append(layer["geometryId"])

    return {"walls": geo_wall_ids, "doors": geo_door_ids}


def update_origin_offset(coordinate):
    global origin_offset
    x = coordinate[0]
    y = coordinate[1]
    if not len(origin_offset):
        origin_offset = [x,y]
    else:
        origin_offset[0] = min(origin_offset[0], x)
        origin_offset[1] = min(origin_offset[1], y)


def geometry_container_to_coordinates_list(geometry_container):
    coordinates_list = []
    
    for polyline in geometry_container:
        coordinate_pairs_list = []
        for coordinate in polyline:
            update_origin_offset(coordinate)
            pair = {
                "x": coordinate[0],
                "y": coordinate[1],
            }
            coordinate_pairs_list.append(pair)
        coordinates_list.append(coordinate_pairs_list)
    
    return coordinates_list

def convert_geometry_to_obstruction_lines(map_data, geometry_ids):
    geometry = map_data["data"]["geometry"]
    obstruction_lines = []
    
    for geometry_id in geometry_ids:
        layer_geometry = geometry[geometry_id]

        for container in layer_geometry["polygons"]:
            polygons_coordinate_list = geometry_container_to_coordinates_list(container)
            obstruction_lines += polygons_coordinate_list

        polylines_coordinate_list = geometry_container_to_coordinates_list(layer_geometry["polylines"])
        obstruction_lines += polylines_coordinate_list
   
    return obstruction_lines


def scale_and_offset_coordinates(obstruction_lines):
    for line in obstruction_lines:
        for coordinate in line:
            coordinate["x"] = (coordinate["x"] - origin_offset[0]) * SCALE
            coordinate["y"] = (coordinate["y"] - origin_offset[1]) * SCALE
    
    return obstruction_lines

# endregion

# region door functions

def get_door_type(polylines, polygons):
    """
    Determines the type of a door based on the given polylines and polygons.

    Args:
        polylines (list): A list of polylines representing the door.
        polygons (list): A list of polygons representing the door.

    Returns:
        str or int: The type of the door. Returns "A" or "B" for valid types, and 0 for an invalid type.
    """
    polylines_count = len(polylines)
    polygons_count = len(polygons[0])

    polylines_point_count = 0
    for polyline in polylines:
        polylines_point_count += len(polyline)

    polygons_point_count = 0
    for polygon in polygons[0]:
        polygons_point_count += len(polygon)

    # rectangle with small wall segments on either end
    if (polylines_count == 2 
            and polygons_count == 1
            and polylines_point_count == 4
            and polygons_point_count == 4):
        return "A"
    
    # just a plain rectangle
    if (polylines_count == 0 
            and polygons_count == 1):
        return "B"

    return 0
        

def calculate_obstruction_line_for_door_A(door_polylines, door_polygons):
    return [{"x":door_polylines[0][0][0], "y":door_polylines[0][0][1]},
            {"x":door_polylines[1][1][0], "y":door_polylines[1][1][1]}]


def calculate_obstruction_line_for_door_B(door_polylines, door_polygons):
    polygon = door_polygons[0][0]

    long_edge = [polygon[0], polygon[1]]  # coordinates start at longe edge
    
    offset = [(polygon[1][0] - polygon[2][0])/2,
              (polygon[1][1] - polygon[2][1])/2]
    
    midline = [[long_edge[0][0] - offset[0], long_edge[0][1] - offset[1]],
               [long_edge[1][0] - offset[0], long_edge[1][1] - offset[1]]]

    return [{"x":midline[0][0], "y":midline[0][1]},
            {"x":midline[1][0], "y":midline[1][1]}]


def generate_door_obstruction_lines(map_data, geometry_ids):
    geometry = map_data["data"]["geometry"]
    obstruction_lines = []
    
    for geometry_id in geometry_ids:
        layer_geometry = geometry[geometry_id]
        door_polylines = layer_geometry["polylines"]
        door_polygons = layer_geometry["polygons"]
        door_type = get_door_type(door_polylines, door_polygons)

        if door_type == 0:
            continue
        elif door_type == "A":
            door_obstruction_line = calculate_obstruction_line_for_door_A(door_polylines, door_polygons)
        elif door_type == "B":
            door_obstruction_line = calculate_obstruction_line_for_door_B(door_polylines, door_polygons)
        
        obstruction_lines.append(door_obstruction_line)

    return obstruction_lines


def calculate_midpoint_between_two_points(p1, p2):
    mx = (p1["x"] + p2["x"]) / 2
    my = (p1["y"] + p2["y"]) / 2
    
    return {"x": mx, "y": my}


def calculate_angle_between_two_points(p1, p2):
    dx = p2["x"] - p1["x"]
    dy = p2["y"] - p1["y"]

    return math.atan2(dy, dx)  # in radians


def generate_portals(map_data, geometry_ids):
    door_obstruction_lines = generate_door_obstruction_lines(map_data, geometry_ids)
    door_obstruction_lines = scale_and_offset_coordinates(door_obstruction_lines)
    portals = []

    for line in door_obstruction_lines:
        position = calculate_midpoint_between_two_points(line[0], line[1])
        rotation = calculate_angle_between_two_points(line[0], line[1])

        portal = {}
        portal["position"] = position
        portal["bounds"] = line
        portal["rotation"] = rotation
        portal["closed"] = True,
        portal["freestanding"] = False
        portals.append(portal)
    
    return portals

# endregion


def dscrawl_to_uvtt(dscrawl_file_name, map_width, map_height, tile_size=70, image_file_name=None):
    """
    Converts a DScrawl file to a UVTT file format.

    Args:
        dscrawl_file_name (str): The name of the DScrawl file to convert.
        map_width (int): The width of the map in cells.
        map_height (int): The height of the map in cells.
        tile_size (int): The size of each tile in pixels.
        image_file_name (str, optional): The name of the image file to include in the UVTT file. Defaults to None.

    Returns:
        None
    """
    dscrawl_map_dict = parse_map_data(dscrawl_file_name)
    geometry_ids = get_geometry_ids(dscrawl_map_dict)

    obstruction_lines = convert_geometry_to_obstruction_lines(dscrawl_map_dict, geometry_ids["walls"])

    obstruction_lines = scale_and_offset_coordinates(obstruction_lines)

    portals = generate_portals(dscrawl_map_dict, geometry_ids["doors"])

    map_dict = generate_map_dict(map_size=[map_width,map_height], cell_size=tile_size)
    map_dict["line_of_sight"] = obstruction_lines
    map_dict["portals"] = portals
    
    if image_file_name:
        with open(image_file_name, mode='rb') as file:
            image = file.read()    
        map_dict["image"] = base64.encodebytes(image).decode('utf-8')

    output_file_name = dscrawl_file_name[:-3] + ".dd2vtt"
    with open(output_file_name, 'w') as file:
        json.dump(map_dict, file, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="convert a DungeonScrawl file to a .dd2vtt file")
    parser.add_argument("dscrawl_file_name", type=str, help="DungeonScrawl file")
    parser.add_argument("map_width", type=int, help="map width (in tiles)")
    parser.add_argument("map_height", type=int, help="map height (in tiles)")
    parser.add_argument("-t", "--tile_size", type=int, default=70, help="singe tile size (in pixels)", metavar="")
    parser.add_argument("-i", "--image", type=str, default=None, help="image file", metavar="")
    args = parser.parse_args()

    dscrawl_to_uvtt(
        args.dscrawl_file_name, args.map_width, 
        args.map_height, args.tile_size, 
        image_file_name=args.image)
