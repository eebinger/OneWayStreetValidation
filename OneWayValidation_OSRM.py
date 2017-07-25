# ---------------------------------------------------------------------------
#
# File Name:
#	OneWayValidation_OSRM.py
#
# Created on:
#	06-27-2017
#
# Created by:
#	Ethan Ebinger
#
# Description: 
# 	Using the Open Source Routing Machine (http://project-osrm.org/), 
#	this script tests whether polyline road segments are digitized in the 
#	proper direction. If they are not, they can be flipped in order to 
#	accurately represent the direction of traffic.
#
#	See API for more details on OSRM call: http://project-osrm.org/docs/v5.7.0/api/#route-service
#
#	Be aware that many roads in MA in Open Street Map are based off the
#	Road Inventory and may not display the proper directionality - compare
#	values with another source(i.e. Google Maps) for further verification.
#
# ---------------------------------------------------------------------------

# 0) Import modules, local variables and input parameters:
import arcpy
import csv
import json
import urllib2
import sys

# The road network to validate. Must be a polyline feature class.
# Input is used only for road segment selection, geoprocessing is not done on this feature class.
road_network = arcpy.GetParameterAsText(0)

# The working geodatabase, where feature classes created are saved.
working_gdb = arcpy.GetParameterAsText(1)

# The name of the feature class created in the working geodatabase that geoprocessing is done on. 
# If the option to flip wrongly digitized routes is set to 'Yes', then this is the feature class 
# in which FlipLines_Edit is run on.
working_fc = arcpy.GetParameterAsText(2)

# The unique identifier for road segments in the Road Network feature class. 
# Used to select (and, if selected, flip) polylines in the Working Feature Class.
unique_id = arcpy.GetParameterAsText(3)
	
# SQL Expression used to select specific road segments in the Working Feature Class, 
# which will be submitted to Open Street Maps . 
# This parameter is optional. Leave blank if no selection by attribute is desired,
# as this tool can identify one-way streets and does not need the SQL Expression to run.
street_select_expression = arcpy.GetParameterAsText(4)

# Distance (in meters) at which to Densify polyline segments.
# It is recommended to use in combination with the SQL Expression, and call
# segments based on length:
#	if Length >= 30: densify_distance = 10 Meters
#	if Length < 30 and Length >= 10: densify_distance = 5 Meters
# 	if Length < 10: densify_distance = 1 Meter
densify_distance = arcpy.GetParameterAsText(5)

# File name for the output of Step 4:
fc_Densify_VertPoints = arcpy.GetParameterAsText(6)
fc_Densify_VertPoints = working_gdb + '\\' + working_fc + '_Densify_VertPoints'

# File name for the output of Step 5:
fc_Densify_VertPoints_Project = arcpy.GetParameterAsText(7)
fc_Densify_VertPoints_Project = fc_Densify_VertPoints + '_WGS84'

# The names of the fields to be exported to a CSV (saved as a .txt file). 
# The default values provided indicate the fields required for successful 
# usage of this tool, although additional fields of interest can be added if desired.
#	Required fields:
#		Unique identifier (i.e. ROADINVENTORY_ID)
#		POINT_X
#		POINT_Y
Value_Field = arcpy.GetParameterAsText(8)
if Value_Field == '#' or not Value_Field:
    Value_Field = unique_id + ";POINT_X;POINT_Y"

# The pathname of the folder where CSVs generated from this script, 
# including a .txt file with the unique ids of road segments to flip, will be saved.
flip_ids_output = arcpy.GetParameterAsText(9)

# File name for the TXT output of Step 6:
csv_output = arcpy.GetParameterAsText(10)
csv_output = flip_ids_output + '\\' + working_fc + '_WGS84_addXY.txt'

# File name for the output of Step 11:
flip_ids_txt = arcpy.GetParameterAsText(11)
flip_ids_txt = flip_ids_output + '\\' + working_fc + "_flip_ids.txt"

# Do you wish to flip the directionality of incorrectly digitized road segments automatically?
# If 'Yes', unique segments identified by the Snap To Roads tool as being digitized 
# in the wrong direction of a one-way street will be edited and the start and end points 
# will be flipped (using FlipLines_Edit: http://desktop.arcgis.com/en/arcmap/10.3/tools/editing-toolbox/flip-line.htm) 
# in the Working Feature Class.
# Else, change field to 'No' to skip processes of flipping polylines for now.
flip_routes = arcpy.GetParameterAsText(12)
if flip_routes == '#' or not flip_routes:
    flip_routes = 'Yes'

# Reclassify road segments as 1-way and 2-way based on OSRM return?
reclassify = arcpy.GetParameterAsText(13)
if reclassify == '#' or not reclassify:
    reclassify = 'No'

# ---------------------------------------------------------------------------

# 1) Feature Class to Feature Class
arcpy.FeatureClassToFeatureClass_conversion(
	in_features = road_network, 
	out_path = working_gdb, 
	out_name = working_fc,
	# where_clause = street_select_expression
)
arcpy.AddMessage("Working feature class created: " + working_gdb + '\\' + working_fc)

# 2) Make Feature Layer from Selection
arcpy.MakeFeatureLayer_management(
	in_features = working_gdb + '\\' + working_fc,
	out_layer = 'road_seg_working',
	where_clause = street_select_expression
)

# 3) Densify
arcpy.Densify_edit(
	in_features = 'road_seg_working', 
	densification_method = "DISTANCE", 
	distance = densify_distance
)
arcpy.AddMessage("Polylines densified by distance every " + str(densify_distance))

# 4) Feature Vertices To Points
arcpy.FeatureVerticesToPoints_management(
	in_features = 'road_seg_working', 
	out_feature_class = fc_Densify_VertPoints,
	point_location = "ALL"
)
arcpy.AddMessage("Polyline vertices saved as Points: " + fc_Densify_VertPoints)

# 5) Project
arcpy.Project_management(
	in_dataset = fc_Densify_VertPoints,
	out_dataset = fc_Densify_VertPoints_Project,
	out_coor_system = "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]",
	transform_method = "WGS_1984_(ITRF00)_To_NAD_1983",
	in_coor_system = "PROJCS['NAD_1983_StatePlane_Massachusetts_Mainland_FIPS_2001',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',200000.0],PARAMETER['False_Northing',750000.0],PARAMETER['Central_Meridian',-71.5],PARAMETER['Standard_Parallel_1',41.71666666666667],PARAMETER['Standard_Parallel_2',42.68333333333333],PARAMETER['Latitude_Of_Origin',41.0],UNIT['Meter',1.0]]"
)
arcpy.AddMessage("Points projected to WGS84: " + fc_Densify_VertPoints_Project)

# 6) Add XY Coordinates
arcpy.AddXY_management(
	in_features = fc_Densify_VertPoints_Project
)

# 7) Export Attribute Table to CSV
arcpy.ExportXYv_stats(
	Input_Feature_Class = fc_Densify_VertPoints_Project, 
	Value_Field = Value_Field, 
	Delimiter = "COMMA", 
	Output_ASCII_File = csv_output, 
	Add_Field_Names_to_Output = "ADD_FIELD_NAMES"
)
arcpy.AddMessage("(lon,lat) points added to field, exported as csv: " + csv_output)


# ---------------------------------------------------------------------------

# 8) Parse CSV to collect (lng,lat) pairs for each unique ID
snap_list = []
snap_list_num = -1
id = ''
prev_id = ''
unique_id = str(unique_id)

with open (csv_output, 'rb') as infile:
	reader = csv.DictReader(infile)
	for row in reader:
		id_val = row[unique_id]
		if id != id_val and id_val != unique_id:
			snap_list.append({'id':int(id_val), 'latlng':[], 'url':'', 'url_reverse':'', 'osm_route': {}, 'osm_route_reverse': {}})
			id = id_val
			prev_id = id_val
			#arcpy.AddMessage("now saving (lat,lng) from id segment " + str(id_val))
			snap_list_num += 1
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])
		elif id == id_val and id_val != unique_id:
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])

# 9) Create URL request for Open Source Route Mapping with each unique id.
for i in snap_list:
	if len(i['latlng'][1:-1]) <= 1:
		continue
	else: 
		snap_param = ''
		for j in i['latlng'][1:-1]:
			snap_param += str(j[1]) + "," + str(j[0])+ ";"
		i['url'] = "http://router.project-osrm.org/route/v1/car/" + snap_param[:-1]
		
		snap_param = ''
		for j in reversed(i['latlng'][1:-1]):
			snap_param += str(j[1]) + "," + str(j[0])+ ";"
		i['url_reverse'] = "http://router.project-osrm.org/route/v1/car/" + snap_param[:-1]
		
arcpy.AddMessage("(lat,lng) pairs, Snap To Roads url request collected for each unique ID.")
	
# 10) For each unique ID, call  Open Source Route Mapping API. If the length of the
#	 route returned != the length of the route in reverse direction, than the road
#	 segment is a one-way street. The segment that is the shortest length represents
#	 the correct direction.
oneway_streets = []
twoway_streets = []
flip_ids = []
skipped_ids = []

for i in snap_list:
	if len(i['latlng'][1:-1]) <= 1:
		arcpy.AddMessage(str(i['id']) + " skipped because too few points (<=1)")
		skipped_ids.append(i['id'])
		continue
	
	# Along Road Network Direction:
	try:
		handle = urllib2.urlopen(i['url'])
		url_return = handle.read()
		i['osm_route'] = json.loads(url_return)
	except:
		arcpy.AddMessage("urllib2 error for " + str(i['id']) +  " --> " + str(sys.exc_info()[0]))
		skipped_ids.append(i['id'])
		continue
	
	# Against Road Network Direction:
	try:
		handle = urllib2.urlopen(i['url_reverse'])
		url_return = handle.read()
		i['osm_route_reverse'] = json.loads(url_return)
	except:
		arcpy.AddMessage("urllib2 error for " + str(i['id']) +  " --> " + str(sys.exc_info()[0]))
		skipped_ids.append(i['id'])
		continue
	
	if i['osm_route']['routes'][0]['distance'] == i['osm_route_reverse']['routes'][0]['distance']:
		arcpy.AddMessage(str(i['id']) + " is Two-Way")
		twoway_streets.append(i['id'])
	elif i['osm_route']['routes'][0]['distance'] > i['osm_route_reverse']['routes'][0]['distance']:
		arcpy.AddMessage(str(i['id']) + " is One-Way, needs to be flipped")
		oneway_streets.append(i['id'])
		flip_ids.append(i['id'])
	elif i['osm_route']['routes'][0]['distance'] < i['osm_route_reverse']['routes'][0]['distance']:
		arcpy.AddMessage(str(i['id']) + " is One-Way, does not need to be flipped")
		oneway_streets.append(i['id'])
		
arcpy.AddMessage("IDs to flip: ")
arcpy.AddMessage(flip_ids)
arcpy.AddMessage("OSRM API called for each unique ID, segments to be flipped collected.")

# 11) Export list of ids to flip (aka "flip_ids") and the whole "snap_list" to CSV
with open (flip_ids_txt, 'wb') as f:
	w = csv.writer(f, delimiter=',')
	w.writerow(flip_ids)
	w.writerow(oneway_streets)
	w.writerow(twoway_streets)
	w.writerow(skipped_ids)
	w.writerow(snap_list)
arcpy.AddMessage("Wrongly digitized polyline segments to saved: " + flip_ids_txt)
		
# ---------------------------------------------------------------------------

# 12) Select Layer By Attribute, Flip Lines (optional)
flip_ids_str = ''
if flip_routes.lower() == 'yes':
	for i in flip_ids:
		flip_ids_str += (str(i) + ",")
	if len(flip_ids_str) > 0:
		arcpy.SelectLayerByAttribute_management(
			in_layer_or_view = 'road_seg_working', 
			selection_type = "NEW_SELECTION", 
			where_clause = unique_id + " IN (" + flip_ids_str[:-1] + ")"
		)
		arcpy.FlipLine_edit(
			in_features = 'road_seg_working'
		)
		arcpy.AddMessage(str(len(flip_ids)) + " wrongly digitized polyline segments flipped to proper direction.")
		
# 13) Reclassify Streets (optional)
if reclassify.lower() == 'yes':
	twoway_streets_str = ''
	for i in twoway_streets:
		twoway_streets_str += (str(i) + ",")
	arcpy.SelectLayerByAttribute_management(
		in_layer_or_view = 'road_seg_working', 
		selection_type = "NEW_SELECTION", 
		where_clause = unique_id + " IN (" + twoway_streets_str[:-1] + ")"
	)
	arcpy.CalculateField_management("road_seg_working","STREETOPERATION",2,"PYTHON_9.3")
		
	oneway_streets_str = ''
	for i in oneway_streets:
		oneway_streets_str += (str(i) + ",")
	arcpy.SelectLayerByAttribute_management(
		in_layer_or_view = 'road_seg_working', 
		selection_type = "NEW_SELECTION", 
		where_clause = unique_id + " IN (" + oneway_streets_str[:-1] + ")"
	)
	arcpy.CalculateField_management("road_seg_working","STREETOPERATION",1,"PYTHON_9.3")

# ---------------------------------------------------------------------------
