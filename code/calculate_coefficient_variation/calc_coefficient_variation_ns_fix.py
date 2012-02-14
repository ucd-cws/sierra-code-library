#-------------------------------------------------------------------------------
# Name:        calc_coefficient_variation
# Purpose:      calculates coefficient of variation on existing
#               mean and standard deviation fields in shps
# Author:      rapeek
#
# Created:     10/12/2011
#-------------------------------------------------------------------------------
# Import system modules
import arcpy
from arcpy import env

# Set environment settings
env.workspace = "E:/FSFISH/multivariate_modeling/ZonalStats.gdb"

# Set local variables:

fieldName = "CVar"
fcFeatures = ["HUC12_dem10m","Slope_Percent_by_HUC12","HUC12_PercentSlope","HUC12_Elevation"]

# Execute AddField for new fields
#
arcpy.AddField_management(fc1, fieldName, "DOUBLE")

for fc in fcFeatures:#add "CVar" field in all tables
    arcpy.AddField_management(fc, fieldName, "DOUBLE")
    cvCur = arcpy.UpdateCursor(fc)

    for row in cvCur:
        row.setValue(fieldName,row.STD / row.MEAN) # your original version of this was correct, but this is more robust because now you only need to update fieldName near the top if the field changes
        cvCur.updateRow(row)
    
    del cvCur, row # Delete cursor and row objects

print arcpy.GetMessages()

