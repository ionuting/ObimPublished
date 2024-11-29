import ifcopenshell
import ifcopenshell.geom
from ifcopenshell.api import run
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
import numpy as np

# Function to create a cube using pythonOCC
def create_cube(x, y, z):
    return BRepPrimAPI_MakeBox(x, y, z).Shape()

# Initialize the IFC file
file = ifcopenshell.file()

# All projects must have one IFC Project element
project = run("root.create_entity", file, ifc_class="IfcProject", name="My Project")

# Assign units (defaults to metric units)
run("unit.assign_unit", file)

# Create a modeling geometry context
context = run("context.add_context", file, context_type="Model")

# Create the 3D body geometry context
body = run("context.add_context", file, context_type="Model",
           context_identifier="Body", target_view="MODEL_VIEW", parent=context)

# Create a site, building, and storey
site = run("root.create_entity", file, ifc_class="IfcSite", name="My Site")
building = run("root.create_entity", file, ifc_class="IfcBuilding", name="Building A")
storey = run("root.create_entity", file, ifc_class="IfcBuildingStorey", name="Ground Floor")

# Aggregate hierarchy
run("aggregate.assign_object", file, relating_object=project, product=site)
run("aggregate.assign_object", file, relating_object=site, product=building)
run("aggregate.assign_object", file, relating_object=building, product=storey)

# Create the cube shape
cube_shape = create_cube(250.0, 250.0, 2800.0)

# Tessellate the cube shape
deflection = 0.5  # Set a deflection for tessellation, adjust as needed
settings = ifcopenshell.geom.settings()
settings.set(settings.USE_BREP_DATA, True)

# Tessellate the geometry
cube_tessellated_shape = ifcopenshell.geom.main.tesselate(file.schema, cube_shape, deflection)

# Create the matrix for the position
x, y, z = 1, 2, 0
rot = 0

# Create a 4x4 identity matrix and rotate it
matrix = np.eye(4)
matrix[:,3][0:3] = (x, y, z)
matrix = ifcopenshell.util.placement.rotation(rot, "Z") @ matrix

# Create the product shape representation
product_representation = cube_tessellated_shape.Representations[0]
product_representation.ContextOfItems = body
file.add(product_representation)

# Create an IfcColumn to hold the shape
column = run("root.create_entity", file, ifc_class="IfcColumn", name="ColumnE1")
print(column)
# Assign the body geometry to the column
run("geometry.assign_representation", file, product=column, representation=product_representation)

# Assign the column to coordinates defined by the matrix
run("geometry.edit_object_placement", file, product=column, matrix=matrix, is_si=True)

# Assign the column to the spatial structure (storey)
file.createIfcRelContainedInSpatialStructure(
    GlobalId=ifcopenshell.guid.new(), 
    RelatedElements=[column], 
    RelatingStructure=storey
)

# Write the IFC file
file.write('cube.ifc')

print("Cube geometry added to cube.ifc")
