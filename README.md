# OneWayStreetValidation.py
Using the Google Maps API Snap To Roads tool, this ArcPy tool tests whether polyline road segments in an ArcGIS road network are digitized in the proper direction. If they are not, they can be flipped in order to accurately represent the direction of traffic.
# Snap To Roads Service: 
More information on the Google Maps Roads API Snap To Roads service can be found here: https://developers.google.com/maps/documentation/roads/snap
# The ArcPy tools used:
Feature Class to Feature Class: http://pro.arcgis.com/en/pro-app/tool-reference/conversion/feature-class-to-feature-class.htm  
Make Feature Layer:  http://pro.arcgis.com/en/pro-app/tool-reference/data-management/make-feature-layer.htm  
Densify Lines: http://pro.arcgis.com/en/pro-app/tool-reference/editing/densify.htm  
Feature Vertices to Points: http://pro.arcgis.com/en/pro-app/tool-reference/data-management/feature-vertices-to-points.htm  
Project: http://pro.arcgis.com/en/pro-app/tool-reference/data-management/project.htm  
Add XY Coordinates to Feature Class: http://pro.arcgis.com/en/pro-app/tool-reference/data-management/add-xy-coordinates.htm  
Export to CSV: http://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-statistics-toolbox/export-feature-attribute-to-ascii.htm  
Flip Lines: http://desktop.arcgis.com/en/arcmap/10.3/tools/editing-toolbox/flip-line.htm  
Add Message: http://pro.arcgis.com/en/pro-app/arcpy/functions/addmessage.htm  
