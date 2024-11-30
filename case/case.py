import csv
import sys
import argparse
from build123d import *


from bd_warehouse.fastener import ButtonHeadScrew, ClearanceHole

parser = argparse.ArgumentParser(prog='katori-case')
parser.add_argument('--export', action="store_true")
parser.add_argument('--power-switch', action="store_true")

args = parser.parse_args(sys.argv[1:])

print(args)
do_export = args.export

if not do_export:
    from ocp_vscode import *

full_assembly = True
do_power_switch = True

bottom_thickness = 2.0 * MM
side_wall_thickness = 2 * MM

pcb_edge_gap = 0.5 * MM

exterior_radius = 2.0 * MM

plate_thickness = 1.2 * MM

# From measuring https://github.com/Cipulot/cipulot_kicad_parts/blob/main/cipulot_parts.3dshapes/Topre_OEM_1U.step
pcb_to_plate_gap = 4.75 * MM

pcb_thickness = 1.6 * MM

socket_height = 0.0 * MM

wall_height_above_plate = 7.0 * MM

# Spec is 7, so we add some wiggle room!
usb_opening_height = 7.2 * MM

reset_opening_height = 4 * MM
reset_opening_spacing = 4 * MM

reset_button_center_height = 0.95 * MM

power_switch_center_height = 1 * MM
power_switch_opening_height = 2.2 * MM
power_switch_opening_spacing = 4 * MM

# From https://www.lcsc.com/datasheet/lcsc_datasheet_2205251630_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf
usb_port_height = 3.26 * MM

# For 3M SJ5382
bumpon_width = 6.4 * MM

bumpon_hole_depth = 1 * MM

assembly_screw = ButtonHeadScrew(size="M3-0.5", length=5)

standoff_height = 2 * MM

total_depth = bottom_thickness + pcb_thickness + standoff_height + pcb_to_plate_gap + plate_thickness + wall_height_above_plate

depth_to_interior_bottom = total_depth - bottom_thickness

def pnp_locations():
    with open(f"pcb/katori_cpl.csv") as file:
        reader = csv.DictReader(file)
        return dict([(x['Designator'],x) for x in reader])

def mounting_holes():
    return [(float(i["Mid X"]), -float(i["Mid Y"])) for i in pnp_locations().values() if i["Package"] == "MountingHole_3mm_Pad_NonPTH_TopOnly"]

locations = pnp_locations()

SVG_FILE = "pcb/katori-User_Eco1.svg"

def get_svg_height():
    import xml.etree.ElementTree as ET
    tree = ET.parse(SVG_FILE)
    root = tree.getroot()

    return float(root.get("height", "0.0mm").removesuffix("mm"))

edge_export = import_svg(SVG_FILE)

with BuildPart() as case:
    with BuildSketch() as edge:
        add(Wire.combine(edge_export.edges(), tol=0.05 * MM).wires()[0].clean().moved(Location((0, -get_svg_height(), 0))))
        make_face()

    offset(edge.faces(), amount=(pcb_edge_gap + side_wall_thickness), kind = Kind.ARC)
    extrude(amount = -total_depth * MM)

#    chamfer(faces().sort_by(Axis.Z)[0].edges(), length=0.001 * MM)
#
#    chamfer(faces().sort_by(Axis.Z)[-1].edges(), length=0.001 * MM)

    offset(edge.face(), amount=pcb_edge_gap, kind = Kind.ARC)
    extrude(amount=-depth_to_interior_bottom, mode=Mode.SUBTRACT)

    with Locations(Plane.XY.reverse().move(Location((0,0,-total_depth)))) as bottom:
        with Locations(mounting_holes()):
            CounterBoreHole(counter_bore_depth=1 * MM, counter_bore_radius=6.3 * MM / 2, radius=3.3 * MM / 2)

    xiao_location = Location((float(locations["U1"]["Mid X"]), float(locations["U1"]["Mid Y"]), -(depth_to_interior_bottom - standoff_height - (2 * pcb_thickness) - socket_height - (usb_port_height / 2))))
    inner_face = faces().filter_by(Plane.YZ.rotated((0,0,90)), tolerance=1).sort_by_distance(xiao_location.position)[0]

    xiao_on_usb_face = xiao_location.position.project_to_plane(Plane(inner_face))

    with BuildSketch(inner_face):
        proj_loc = project(xiao_on_usb_face, mode = Mode.PRIVATE)
        with Locations(*proj_loc):
            SlotCenterToCenter(center_separation=6.5, height=usb_opening_height)
    
    extrude(amount=-(70 * MM), mode=Mode.SUBTRACT)

    if do_power_switch:
        power_location = Location((float(locations["SW31"]["Mid X"]), float(locations["SW31"]["Mid Y"]), -(depth_to_interior_bottom - standoff_height + power_switch_center_height)))
        power_inner_face = faces().filter_by(Plane.YZ.rotated((0,0,90)), tolerance=1.0).sort_by_distance(power_location.position)[0]

        power_on_usb_face = power_location.position.project_to_plane(Plane(power_inner_face))

        with BuildSketch(power_inner_face):
            proj_loc = project(power_on_usb_face, mode = Mode.PRIVATE)
            with Locations(*proj_loc):
                SlotCenterToCenter(center_separation=power_switch_opening_spacing, height=power_switch_opening_height)
        
        extrude(amount=-(side_wall_thickness), mode=Mode.SUBTRACT, taper=-20.0)

    with BuildSketch(faces().sort_by(Axis.Z)[0]):
        with Locations([project(Vector((float(i["Mid X"]), float(i["Mid Y"]), 0)), mode = Mode.PRIVATE) for i in locations.values() if i["Package"] == "Bumpon"]):
            Circle(radius = (bumpon_width * 1.1) / 2)
    extrude(amount = -bumpon_hole_depth, mode = Mode.SUBTRACT)

if do_export:
    export_step(case.part, "katori-case.step")
    export_stl(case.part, "katori-case.stl")
else:
    if full_assembly:
        pcb_and_parts = import_step("pcb/katori-3D.step")

        pcb_and_parts.locate(Location([0, 0, -(depth_to_interior_bottom - standoff_height)]))

        plate = import_step("plate/katori-plate-3D.step")
        plate.locate(Location([3, 0, -(depth_to_interior_bottom - standoff_height - pcb_to_plate_gap - pcb_thickness - (0.1 * MM))]))

        assy = Compound(label="assembly", children=[case.part, pcb_and_parts, plate])

        show_object(assy)
    else:
        show_object(case.part)
        
