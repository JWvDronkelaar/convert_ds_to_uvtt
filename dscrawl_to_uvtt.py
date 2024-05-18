import base64
import argparse
import json
import math
import re

DESCRIPTION = "Convert a DungeonScrawl file to a .dd2vtt file."
VERSION = "1.0.0"
USE_GOOEY = True

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
                and (polygons_point_count == 4 or polygons_point_count == 5)):
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

    print(f"File '{output_file_name}' created successfully.")

if USE_GOOEY:
    from gooey import Gooey, GooeyParser

    @Gooey(program_name='Dungeon Scrawl to UVTT', image_dir='C:/Users/JW/Documents/vscode/convert_ds_to_uvtt/images', show_stop_warning=False, show_success_modal=False, header_bg_color="#FBAB7E", default_size=(550, 630))
    def parse_arguments_with_gooey():
        parser = GooeyParser(description=DESCRIPTION)

        optional_group = parser.add_argument_group("Optional arguments", gooey_options={"columns": 1})

        parser.add_argument("dscrawl_file_name", help="The name of the DungeonScrawl file to convert.", metavar="Dungeon Scrawl file", widget="FileChooser", gooey_options={"full_width": True})
        parser.add_argument("map_width", help="The width of the map in tiles.", type=int, action="store", metavar="Map width")
        parser.add_argument("map_height", help="The height of the map in tiles.", type=int, action="store", metavar="Map height")
        optional_group.add_argument("-i", "--image_file_name", help="The name of the image file to include.", default=None, metavar="Image file", widget="FileChooser", gooey_options={"full_width": True})
        optional_group.add_argument("-t", "--tile_size", help="The size of a single tile in pixels.", default=70, type=int, action="store", metavar="Tile size")
        
        return parser.parse_args()


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("dscrawl_file_name", help="The name of the DungeonScrawl file to convert.", metavar="Dungeon Scrawl file")
    parser.add_argument("map_width", help="The width of the map in tiles.", type=int, metavar="Map width")
    parser.add_argument("map_height", help="The height of the map in tiles.", type=int, metavar="Map height")
    parser.add_argument("-i", "--image_file_name", help="The name of the image file to include.", default=None, metavar="Image file")
    parser.add_argument("-t", "--tile_size", help="The size of a single tile in pixels.", default=70, type=int, metavar="Tile size")
    
    return parser.parse_args()


if __name__ == "__main__":
    if USE_GOOEY:
        args = parse_arguments_with_gooey()
    else:
        args = parse_arguments()

    dscrawl_to_uvtt(args.dscrawl_file_name, args.map_width, args.map_height, args.tile_size, args.image_file_name)
