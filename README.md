# OneWayStreetValidation.py
Using the Google Maps API Snap To Roads service and the the Open Source Routing Machine (OSRM), this script tests whether polyline road segments are digitized in the proper direction. If they are not, they can be flipped in order to accurately represent the direction of traffic.

This script is meant to be used to create a ArcGIS script tool, although it can also be run from the command line.

To compare road segments using only Snap to Roads, use: 'OneWayStreetValidation_SnapToRoads.py'

To compare road segments using only OSRM, use: 'OneWayStreetValidation_OSRM.py'
# Snap To Roads Service: 
More information on the Google Maps Roads API Snap To Roads service can be found here:
https://developers.google.com/maps/documentation/roads/snap
# Open Source Routing Machine
More information on the Open Source Routing Machine can be found here:
http://project-osrm.org/docs/v5.7.0/api/#route-service
# Road Directionality Validation:
This script was written to circumvent manual editing of a GIS polyline feature class by using online mapping services to validate the directionality of road segments in an existing road network.

The tool takes as input a road network in the form of a polyline shapefile or feature class with uniquely identified segments. The tool first <a href="http://pro.arcgis.com/en/pro-app/tool-reference/editing/densify.htm">densifies</a> the polyline feature class to create additional vertices along the road segment, then converts the <a href="http://pro.arcgis.com/en/pro-app/tool-reference/data-management/feature-vertices-to-points.htm">feature vertices to points</a>. Polylines should be densified based on their length.

Next, the points are <a href="http://pro.arcgis.com/en/pro-app/tool-reference/data-management/project.htm">projected</a> to the 1984 World Geodetic System (WGS 84)/Web Mercator projection. This tool was built based on a road network in Massachusetts, so if another state is used then the input coordinate system should be redefined in the script.

Then, <a href="http://pro.arcgis.com/en/pro-app/tool-reference/data-management/add-xy-coordinates.htm">XY Coordinates</a> are added to the projected point feature class, and the relevant fields are <a href="http://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-statistics-toolbox/export-feature-attribute-to-ascii.htm">exported to a CSV</a>.

For each unique ID a HTTP request is generated to submit the route through OSRM and the Snap to Roads service. One way streets and two way streets are identified, as are improperly digitized road segments. Finally, the user can decide whether to just save the returned unique ids or to <a href="http://pro.arcgis.com/en/pro-app/tool-reference/data-management/calculate-field.htm">recaluclate</a> the street operation attribute field and/or <a href="http://desktop.arcgis.com/en/arcmap/10.3/tools/editing-toolbox/flip-line.htm">flip</a> the directionality of the polylines.
