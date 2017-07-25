# ---------------------------------------------------------------------------
#
# File Name:
#	OneWayValidation.py
#
# Created on:
#	06-06-2017
#
# Created by:
#	Ethan Ebinger
#
# Description: 
# 	Using the Google Maps API Snap To Roads tool, this script tests whether 
#	polyline road segments are digitized in the proper direction. If they are 
#	not, they can be flipped in order to accurately represent the direction 
#	of traffic.
#	Information on the Google Maps API Snap To Roads tool can be found here: 
#	https://developers.google.com/maps/documentation/roads/snap
#
# ---------------------------------------------------------------------------

# 0) Import modules, define Google Maps API Key, local variables and input parameters:
import arcpy
import csv
import json
import urllib2
import math

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
# which will be submitted to Google Maps API for the Snap To Roads tool. 
# This parameter is optional. Leave blank if no selection by attribute is desired.
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

# Your Google Maps API Key. Should be a 39 character string acquired through 
# creation of credentials via the Google API Manager: 
#	https://console.developers.google.com/apis/credentials.
# Required to run tool successfully. 
# If you have a premium key, there are no limits on the usage of this tool. 
# Otherwise, only 2500 requests (i.e. road segments) can be made each day: 
#	https://developers.google.com/maps/documentation/roads/snap
key = arcpy.GetParameterAsText(9)

# Do you wish to flip the directionality of incorrectly digitized road segments automatically?
# If 'Yes', unique segments identified by the Snap To Roads tool as being digitized 
# in the wrong direction of a one-way street will be edited and the start and end points 
# will be flipped (using FlipLines_Edit: http://desktop.arcgis.com/en/arcmap/10.3/tools/editing-toolbox/flip-line.htm) 
# in the Working Feature Class.
# Else, change field to 'No' to skip processes of flipping polylines for now.
flip_routes = arcpy.GetParameterAsText(10)
if flip_routes == '#' or not flip_routes:
    flip_routes = 'Yes'

# The pathname of the folder where CSVs generated from this script, 
# including a .txt file with the unique ids of road segments to flip, will be saved.
flip_ids_output = arcpy.GetParameterAsText(11)

# File name for the TXT output, from (7):
csv_output = arcpy.GetParameterAsText(12)
csv_output = fc_Densify_VertPoints_Project + '_addXY.txt'

# File name for the output of Step 11:
flip_ids_txt = arcpy.GetParameterAsText(13)
flip_ids_txt = flip_ids_output + '\\' + working_fc + "_flip_ids.txt"

# Function from https://gist.github.com/jeromer/2005586 that is used to calculate
# the orientation of the sent and returned lines to verify if it was snapped to the
# correct road:
def calculate_initial_compass_bearing(pointA, pointB):
	if (type(pointA) != tuple) or (type(pointB) != tuple):
		raise TypeError("Only tuples are supported as arguments")
	lat1 = math.radians(pointA[0])
	lat2 = math.radians(pointB[0])
	diffLong = math.radians(pointB[1] - pointA[1])
	x = math.sin(diffLong) * math.cos(lat2)
	y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))
	initial_bearing = math.atan2(x, y)
	initial_bearing = math.degrees(initial_bearing)
	compass_bearing = (initial_bearing + 360) % 360
	return compass_bearing

# ---------------------------------------------------------------------------

# 1) Feature Class to Feature Class
arcpy.FeatureClassToFeatureClass_conversion(
	in_features = road_network, 
	out_path = working_gdb, 
	out_name = working_fc
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
arcpy.AddMessage( "Polylines densified by distance every " + str(densify_distance))

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

# 8) Parse CSV to collect (lat,lng) pairs for each unique ID
roadInvIDs = []
snap_list = []
row_num = 0
snap_list_num = -1
id = ''
prev_id = ''
unique_id = str(unique_id)

with open (csv_output, 'rb') as infile:
	reader = csv.DictReader(infile)
	for row in reader:
		id_val = row[unique_id]
		if id != id_val and id_val != unique_id:
			snap_list.append({'id':int(id_val), 'latlng':[], 'url':'', 'snapped_points': {}})
			id = id_val
			prev_id = id_val
			roadInvIDs.append(id_val)
			#arcpy.AddMessage("now saving (lat,lng) from id segment " + str(id_val))
			snap_list_num += 1
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])
		elif id == id_val and id_val != unique_id:
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])
		row_num += 1

# 9) Create URL request for Snap To Roads tool for each id.
#	 In order to make sure the request properly runs, no more than 100 points can
#	 be submitted at the same time, hense the if/else statement and the cutoff.
for i in snap_list:
	snap_param = ''
	if len(i['latlng'][1:-1]) <= 1:
		continue
	elif len(i['latlng']) > 102:
		for j in i['latlng'][1:101]:
			snap_param += str(j[0]) + "," + str(j[1])+ "|"
	else: 
		for j in i['latlng'][1:-1]:
			snap_param += str(j[0]) + "," + str(j[1])+ "|"
	i['url'] = "https://roads.googleapis.com/v1/snapToRoads?path=" + snap_param[:-1] + "&interpolate=false&key=" + key

arcpy.AddMessage("(lat,lng) pairs, Snap To Roads url request collected for each unique ID.")
	
# 10) For each unique ID, call Snap To Roads via Google Maps Roads API. If the 
#	  number of points returned != the number of points sent, then the road 
#	  segment needs to be flipped and the id is saved in "flip_ids" list.
#	  Some records are skipped because they are either too short or are not present
#	  in Google Maps, so those are saved in the "skipped_ids" list.
#	  Other road segments that may need to be flipped but were still returned as
#	  snapped by the Snap To Roads service are saved in the "potential_flip_ids" list
#	  and should be manually reviewed in ArcGIS by the user.
flip_ids = []
potential_flip_ids = []
skipped_ids = []

if len(snap_list) > 2500:
	arcpy.AddMessage("List is greater than 2500 points. Only the first 2500 values in 'snap_list' were queried.")
for i in snap_list[:2499]:
	#arcpy.AddMessage(i['id'])
	if len(i['latlng'][1:-1]) <= 1:
		#arcpy.AddMessage("id " + str(i['id']) + " skipped because too few points (<=1)")
		skipped_ids.append(i['id'])
		continue
	#elif len(i['latlng']) > 102:
		#arcpy.AddMessage("# of points sent = 100")
	#else:
		#arcpy.AddMessage("# of points sent = " + str(len(i['latlng'][1:-1])))
	handle = urllib2.urlopen(i['url'])
	url_return = handle.read()
	snapped_points = json.loads(url_return)
	if len(snapped_points) != 1:
		#arcpy.AddMessage("id " + str(i['id']) + " skipped because segment not in Google Maps")
		skipped_ids.append(i['id'])
		continue
	else:
		i['snapped_points'] = snapped_points['snappedPoints']
		#arcpy.AddMessage("# of points recieved = " + str(len(i['snapped_points'])))
		if len(i['latlng']) > 102:
			if len(i['snapped_points']) != 100:
				flip_ids.append(i['id'])
		else:
			if len(i['latlng'][1:-1]) != len(i['snapped_points']):
				flip_ids.append(i['id'])
			else: 
				lat_start = float(i['latlng'][1][0])
				lat_end = float(i['latlng'][-2][0])
				lng_start = float(i['latlng'][1][1])
				lng_end = float(i['latlng'][-2][1])
				
				snap_lat_start = i['snapped_points'][0]['location']['latitude']
				snap_lat_end = i['snapped_points'][-1]['location']['latitude']
				snap_lng_start = i['snapped_points'][0]['location']['longitude']
				snap_lng_end = i['snapped_points'][-1]['location']['longitude']
				
				orig_distance = math.sqrt(math.pow(lat_end - lat_start,2)+math.pow(lng_end - lng_start,2))
				snap_distance = math.sqrt(math.pow(snap_lat_end - lat_start,2)+math.pow(snap_lng_end - lng_start,2))
				if (abs(snap_distance - orig_distance)*100000) > 4:		# empirically derived
					#arcpy.AddMessage("manually check id " + str(i['id']) + " b/c snap distances off")
					potential_flip_ids.append(i['id'])
								
				dir_orig = calculate_initial_compass_bearing((lat_start, lng_start),(lat_end, lng_end))
				dir_snap = calculate_initial_compass_bearing((snap_lat_start, snap_lng_start),(snap_lat_end, snap_lng_end))
				if (abs(dir_orig - dir_snap)) > 2:		# empirically derived
					#arcpy.AddMessage("manually check id " + str(i['id']) + " b/c snap orientation off")
					if i['id'] in potential_flip_ids:
						flip_ids.append(i['id'])
					else:
						potential_flip_ids.append(i['id'])

arcpy.AddMessage("IDs to flip: ")
arcpy.AddMessage(flip_ids)
arcpy.AddMessage("IDs to check manually and potentially flip: ")
arcpy.AddMessage(potential_flip_ids)
arcpy.AddMessage("IDs that were skipped: ")
arcpy.AddMessage(skipped_ids)
arcpy.AddMessage("Snap To Roads called for each unique ID, segments to be flipped collected.")

# 11) Export list of ids to flip (aka "flip_ids") and the whole "snap_list" to CSV
with open (flip_ids_txt, 'wb') as f:
	w = csv.writer(f, delimiter=',')
	w.writerow(flip_ids)
	w.writerow(potential_flip_ids)
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

# ---------------------------------------------------------------------------
