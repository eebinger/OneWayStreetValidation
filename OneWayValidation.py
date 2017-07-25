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
# 	Using the Google Maps API Snap To Roads service and the the Open Source
#	Routing Machine, this script tests whether polyline road segments are 
#	digitized in the proper direction. If they are not, they can be flipped
#	in order to accurately represent the direction of traffic.
#
#	Information on the Google Maps API Snap To Roads tool can be found here: 
#	https://developers.google.com/maps/documentation/roads/snap
#
#	Information on the Open Source Routing Machine can be found here:
#	http://project-osrm.org/docs/v5.7.0/api/#route-service
#
#	Be aware that many roads in MA in Open Street Map are based off the
#	Road Inventory and may not display the proper directionality - compare
#	values with another source(i.e. Google Maps) for further verification.
#
# ---------------------------------------------------------------------------

# 0) Import modules, define Google Maps API Key, local variables and input parameters:
import arcpy
import csv
import json
import urllib2
import math
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

# The pathname of the folder where CSVs generated from this script, 
# including a .txt file with the unique ids of road segments to flip, will be saved.
flip_ids_output = arcpy.GetParameterAsText(10)

# File name for the TXT output of Step 6:
csv_output = arcpy.GetParameterAsText(11)
csv_output = flip_ids_output + '\\' + working_fc + '_WGS84_addXY.txt'

# File names for the output of Step 11:
flip_ids_txt = arcpy.GetParameterAsText(12)
flip_ids_txt = flip_ids_output + '\\' + working_fc + "_flip_ids.txt"

# Do you wish to flip the directionality of incorrectly digitized road segments automatically?
# If 'Yes', unique segments identified by the Snap To Roads tool as being digitized 
# in the wrong direction of a one-way street will be edited and the start and end points 
# will be flipped (using FlipLines_Edit: http://desktop.arcgis.com/en/arcmap/10.3/tools/editing-toolbox/flip-line.htm) 
# in the Working Feature Class.
# Else, change field to 'No' to skip processes of flipping polylines for now.
flip_routes = arcpy.GetParameterAsText(13)
if flip_routes == '#' or not flip_routes:
    flip_routes = 'Yes'

# Reclassify road segments as 1-way and 2-way based on OSRM return?
reclassify = arcpy.GetParameterAsText(14)
if reclassify == '#' or not reclassify:
    reclassify = 'Yes'

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
	
# Timing decorator function adapted from:
# https://www.andreas-jung.com/contents/a-python-decorator-for-measuring-the-execution-time-of-methods
# Timer added to track the speed of the two APIs (how many road segments are processed per second).
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        arcpy.AddMessage('%r %2.2f sec' % \
              (method.__name__, te-ts))
        return result
    return timed

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

# 8) Parse CSV to collect (lat,lng) pairs for each unique ID
snap_list = []
with open (csv_output, 'rb') as infile:
	snap_list_num = -1
	id = ''
	prev_id = ''
	unique_id = str(unique_id)
	reader = csv.DictReader(infile)
	for row in reader:
		id_val = row[unique_id]
		if id != id_val and id_val != unique_id:
			snap_list.append({
				'id':int(id_val),
				'latlng':[],
				#'url_google':'',
				#'url_osrm':'',
				#'url_osrm_reverse':'',
				#'snapped_points': {},
				#'osrm_route': {},
				#'osrm_route_reverse': {}
			})
			id = id_val
			prev_id = id_val
			#arcpy.AddMessage("now saving (lat,lng) from id segment " + str(id_val))
			snap_list_num += 1
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])
		elif id == id_val and id_val != unique_id:
			snap_list[snap_list_num]['latlng'].append([row['POINT_Y'],row['POINT_X']])
	
# 9) For each unique ID, call the Open Source Route Mapping API, then submit 
#	  the returned one-way streets to Snap To Roads via the Google Maps Roads API.
#
#	  OSRM 	-->	If the length of the route returned != the length of the route in 
#				the reverse direction, then the road segment is a one-way street. 
#				The segment that is the shortest length represents the correct direction.
#			--> One-way road segments are saved to the "oneway_streets" list and two-way 
#				road segments are saved to the "twoway_streets" list.
#			--> One-way streets that need to be flipped are saved to the "flip_ids" list.
#			--> Segments with sys errors or are too short in length are appended to the
#				"skipped_ids" list.

osrm_flip = []
osrm_oneway = []
osrm_twoway = []
osrm_skip = []
osrm_error = []

@timeit
def osrm(snap_list):
	for i in snap_list:
		id = int(i['id'])
		if len(i['latlng'][1:-1]) <= 1:
			#arcpy.AddMessage(str(id) + " skipped because too few points (<=1)")
			osrm_skip.append(id)
			continue
		else: 
			# Create URL request for Snap To Roads tool for each id.
			snap_param = ''
			for j in i['latlng'][1:-1]:
				snap_param += str(j[1]) + "," + str(j[0])+ ";"
			url = "http://router.project-osrm.org/route/v1/car/" + snap_param[:-1]
			
			snap_param = ''
			for j in reversed(i['latlng'][1:-1]):
				snap_param += str(j[1]) + "," + str(j[0])+ ";"
			url_reverse = "http://router.project-osrm.org/route/v1/car/" + snap_param[:-1]
			#arcpy.AddMessage("OSRM url request created")
		
			# Along Road Network Direction:
			try:
				handle = urllib2.urlopen(url)
				url_return = handle.read()
				osm_route = json.loads(url_return)
			except:
				#arcpy.AddMessage("urllib2 error for " + str(id) +  " --> " + str(sys.exc_info()[0]))
				osrm_error.append(id)
				continue
			
			# Against Road Network Direction:
			try:
				handle = urllib2.urlopen(url_reverse)
				url_return = handle.read()
				osm_route_reverse = json.loads(url_return)
			except:
				#arcpy.AddMessage("urllib2 error for " + str(id) +  " --> " + str(sys.exc_info()[0]))
				osrm_error.append(id)
				continue
			
			if osm_route['routes'][0]['distance'] == osm_route_reverse['routes'][0]['distance']:
				#arcpy.AddMessage(str(id) + " is Two-Way")
				osrm_twoway.append(id)
			elif osm_route['routes'][0]['distance'] > osm_route_reverse['routes'][0]['distance']:
				arcpy.AddMessage(str(id) + " is One-Way, needs to be flipped")
				osrm_oneway.append(id)
				osrm_flip.append(id)
			elif osm_route['routes'][0]['distance'] < osm_route_reverse['routes'][0]['distance']:
				#arcpy.AddMessage(str(id) + " is One-Way, does not need to be flipped")
				osrm_oneway.append(id)
					
	arcpy.AddMessage("OSRM API called for each unique ID")
	arcpy.AddMessage("OSRM identified " + str(len(osrm_flip)) + " ids to flip")
	arcpy.AddMessage("OSRM identified " + str(len(osrm_oneway)) + " one-way streets")
	arcpy.AddMessage("OSRM identified " + str(len(osrm_twoway)) + " two-way streets")
	arcpy.AddMessage("OSRM skipped " + str(len(osrm_skip) + len(osrm_error)) + " ids")
	
osrm(snap_list)

#	  Snap to Roads --> If the number of points returned != the number of points sent,
#	  					then the road segment needs to be flipped and the id is saved 
#						in the "flip_ids" list. Or, if the geometry of the route is too
#						dissimilar from the snapped path then the segment was snapped to
#						the wrong road and can be flagged as one-way because of improper
#						routing.
#	  				--> Some records are skipped because they are either too short or 
#						are not present in Google Maps. These ids are saved in the 
#						"skipped_ids" list.
#	  				--> Other road segments that may need to be flipped but were still 
#						returned as snapped by the Snap To Roads service are saved in 
#						the "potential_flip_ids" list and should be manually reviewed 
#						in ArcGIS by the user.

google_flip = []
google_potential_flip = []
google_skip = []
google_error = []

@timeit
def snaptoroads(snap_list):
	if len(snap_list) > 2500:
		arcpy.AddMessage("List is greater than 2500 points. The Snap to Roads call will be skipped, please retry tool with less than 2500 road segments.")
		return
	else:	
		for i in snap_list:
			id = int(i['id'])
			if id not in osrm_oneway or osrm_error:
				#arcpy.AddMessage("id " + str(id) + " is either too short or a two-way street, do not need to submit through Snap to Roads")
				continue
			if len(i['latlng'][1:-1]) <= 1:
				#arcpy.AddMessage("id " + str(id) + " skipped because too few points (<=1)")
				google_skip.append(id)
				continue
			
			# Create URL request for Snap To Roads tool for each id.
			# In order to make sure the Snap to Roads request properly runs, no more than 
			# 100 points can be submitted at the same time, hense the if/else statement and the cutoff.
			snap_param = ''
			if len(i['latlng']) > 102:
				n_sent = 100
				for j in i['latlng'][1:101]:
					snap_param += str(j[0]) + "," + str(j[1])+ "|"
			else: 
				n_sent = len(i['latlng'][1:-1])
				for j in i['latlng'][1:-1]:
					snap_param += str(j[0]) + "," + str(j[1])+ "|"
			url = "https://roads.googleapis.com/v1/snapToRoads?path=" + snap_param[:-1] + "&interpolate=false&key=" + key
			#arcpy.AddMessage("Snap To Roads url request created")
			
			try:
				handle = urllib2.urlopen(url)
				url_return = handle.read()
				snapped_points = json.loads(url_return)
			except:
				#arcpy.AddMessage("urllib2 error for " + str(id) +  " --> " + str(sys.exc_info()[0]))
				google_error.append(id)
				continue
			
			if len(snapped_points) != 1:
				#arcpy.AddMessage("id " + str(id) + " skipped because segment not in Google Maps")
				#skipped_ids.append(id)
				continue
			else:
				n_returned = len(snapped_points['snappedPoints'])
				#i['snapped_points'] = snapped_points['snappedPoints']
				#arcpy.AddMessage("# of points recieved = " + str(n_returned))
				if n_sent != n_returned:
					arcpy.AddMessage(str(id) + " is One-Way, needs to be flipped")
					google_flip.append(id)
				else: 
					# n_sent === n_returned, but need to verify that the path was snapped to the proper
					# road, which is done by comparing geometries
					lat_start = float(i['latlng'][1][0])
					lat_end = float(i['latlng'][-2][0])
					lng_start = float(i['latlng'][1][1])
					lng_end = float(i['latlng'][-2][1])
					
					snap_lat_start = snapped_points['snappedPoints'][0]['location']['latitude']
					snap_lat_end = snapped_points['snappedPoints'][-1]['location']['latitude']
					snap_lng_start = snapped_points['snappedPoints'][0]['location']['longitude']
					snap_lng_end = snapped_points['snappedPoints'][-1]['location']['longitude']
					
					orig_distance = math.sqrt(math.pow(lat_end - lat_start, 2) + math.pow(lng_end - lng_start, 2))
					snap_distance = math.sqrt(math.pow(snap_lat_end - lat_start, 2) + math.pow(snap_lng_end - lng_start, 2))
					if (abs(snap_distance - orig_distance)*100000) > 4:		# empirically derived
						#arcpy.AddMessage("manually check id " + str(id) + " b/c snap distance is off")
						google_potential_flip.append(id)	
									
					dir_orig = calculate_initial_compass_bearing((lat_start, lng_start),(lat_end, lng_end))
					dir_snap = calculate_initial_compass_bearing((snap_lat_start, snap_lng_start),(snap_lat_end, snap_lng_end))
					if (abs(dir_orig - dir_snap)) > 2:		# empirically derived
						#arcpy.AddMessage("manually check id " + str(id) + " b/c snap orientation off")
						if id in google_potential_flip:
							# Both the orientation and direction are off, so the road was not properly snapped 
							# and is a one-way street in wrong direction
							google_flip.append(id)
						else:
							google_potential_flip.append(id)
	
	arcpy.AddMessage("Snap To Roads called for each unique ID")
	arcpy.AddMessage("Snap To Roads identified " + str(len(google_flip)) + " ids to flip")
	arcpy.AddMessage("Snap To Roads identified " + str(len(google_potential_flip)) + " ids to manually check")
	arcpy.AddMessage("Snap To Roads skipped " + str(len(google_skip)) + " ids")

snaptoroads(snap_list):

# 10) Export lists of ids to JSON, save object as txt file
results = {
	'flip' 		: [],
	'skip' 		: osrm_skip + google_skip,
	'oneway'	: osrm_oneway,
	'twoway' 	: osrm_twoway,
	'error' 	: osrm_skip + google_error,
}

results['flip'] = google_flip
for i in osrm_flip:
	if i not in google_flip:
		google_flip.append(i)

with open(flip_ids_txt, 'w') as outfile:
	json.dump(results, outfile)
	
arcpy.AddMessage("Wrongly digitized polyline segments to saved: " + flip_ids_txt)
arcpy.AddMessage("Total number of routes to flip = " + str(len(results['flip'])))
		
# ---------------------------------------------------------------------------

# 12) Select Layer By Attribute, Flip Lines (optional)
flip_ids_str = ''
if flip_routes.lower() == 'yes':
	for i in results['flip']:
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
		arcpy.AddMessage(str(len(results['flip'])) + " wrongly digitized polyline segments flipped to proper direction.")

# 13) Reclassify Street Operation Attribute Field (optional)
if reclassify.lower() == 'yes':
	twoway_streets_str = ''
	for i in results['twoway']:
		twoway_streets_str += (str(i) + ",")
	arcpy.SelectLayerByAttribute_management(
		in_layer_or_view = 'road_seg_working', 
		selection_type = "NEW_SELECTION", 
		where_clause = unique_id + " IN (" + twoway_streets_str[:-1] + ")"
	)
	arcpy.CalculateField_management("road_seg_working","STREETOPERATION",2,"PYTHON_9.3")
		
	oneway_streets_str = ''
	for i in results['oneway']:
		oneway_streets_str += (str(i) + ",")
	arcpy.SelectLayerByAttribute_management(
		in_layer_or_view = 'road_seg_working', 
		selection_type = "NEW_SELECTION", 
		where_clause = unique_id + " IN (" + oneway_streets_str[:-1] + ")"
	)
	arcpy.CalculateField_management("road_seg_working","STREETOPERATION",1,"PYTHON_9.3")
		
# ---------------------------------------------------------------------------
