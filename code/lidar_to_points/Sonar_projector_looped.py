#-------------------------------------------------------------------------------
# Name:        Lowrance Sonar Data Project
# Purpose:
#
# Author:      Eric
#
# Created:     26/10/2013
# Copyright:   (c) Eric 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# MakeXYLayer.py
# Description: Creates an XY layer and exports it to a layer file

# import system modules
import arcpy
from arcpy import env
import os

# Set environment settings
env.workspace = r"C:\Users\Eric\Documents\USFWS\Bathymetry_project\Bathymetry\Pond_bathymetry\Sonar\data\Processed_sonar"

tableList = arcpy.ListFiles("*.dbf")
for table in tableList:
    print table
    # Set the local variables
    in_Table = table
    x_coords = "PositionX"
    y_coords = "PositionY"
    z_coords = "depth"
    out_Layer = os.path.splitext(table)[0]
    saved_Layer = os.path.join('C:\Users\Eric\Documents\USFWS\Bathymetry_project\Bathymetry\Pond_bathymetry\Sonar\Output\Features', out_Layer)
    #r"C:\Users\Eric\Documents\USFWS\Bathymetry_project\Bathymetry\Pond_bathymetry\Sonar\Output\Features\Sonar\M395Compiled_noZeros.lyr"
    print(saved_Layer)
    # Set the spatial reference
    spRef = r"C:\Users\Eric\Documents\USFWS\Bathymetry_project\Modoc\Shapes\Sonar_pts_LowrMercator.prj"

    # Make the XY event layer...
    arcpy.MakeXYEventLayer_management(in_Table, x_coords, y_coords, out_Layer, spRef, z_coords)

    # Print the total rows
    print arcpy.GetCount_management(out_Layer)
    print arcpy.Describe(out_Layer).spatialReference.name

    # Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
    # The following inputs are layers or table views: "M395_Compiled_noZeros"
    #arcpy.Project_management(out_Layer,"C:/Users/Eric/Documents/USFWS/Bathymetry_project/Bathymetry/Pond_bathymetry/Sonar/Output/Features/Sonar/M395_Compiled_noZeros_utm.shp","PROJCS['NAD_1983_UTM_Zone_10N',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-123.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]","#","PROJCS['Test_Lowrance_Mercator',GEOGCS['Custom_Sphere',DATUM['D_Custom_Sphere',SPHEROID['Custom_Sphere',6356752.3142,0.0]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Mercator'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',0.0],PARAMETER['Standard_Parallel_1',0.0],UNIT['Meter',1.0]]")

    # Save to a layer file
    print("saving layer file")
    #arcpy.SaveToLayerFile_management(out_Layer, saved_Layer)

    outfc = os.path.join('C:\Users\Eric\Documents\USFWS\Bathymetry_project\Bathymetry\Pond_bathymetry\Sonar\Output\Features\Sonar\All_points', "%s.shp" %out_Layer)
    print(outfc)
    outCS = r"C:\Program Files (x86)\ArcGIS\Desktop10.0\Coordinate Systems\Projected Coordinate Systems\UTM\NAD 1983\NAD 1983 UTM Zone 10N.prj"

    arcpy.Project_management(out_Layer, outfc, outCS)
    #arcpy.FeatureClassToFeatureClass_conversion(out_Layer,"C:\Users\Eric\Documents\USFWS\Bathymetry_project\Bathymetry\Pond_bathymetry\Sonar\Output\Features\Sonar","M395_Compiled_LowrMerc.shp")

    print("all done")
