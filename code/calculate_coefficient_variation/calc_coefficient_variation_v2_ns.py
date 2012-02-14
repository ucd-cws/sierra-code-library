#-------------------------------------------------------------------------------
# Name:        calc_coefficient_variation
# Purpose:      calculates coefficient of variation on existing
#               mean and standard deviation fields in shps
# Author:      rapeek
#
# Created:     10/12/2011
#-------------------------------------------------------------------------------
# Import system modules
import os, arcpy

# Set environment settings
arcpy.env.workspace = r"E:/Home/rapeek/Private/PISCES/tables/BCM_ppt"

# Set local variables:
fieldName = "CVar"

# List tables in mdb
tables = arcpy.ListTables()

print len(tables)

try:
    for fc in tables:#add "CVar" field in all tables
        print "processing %s" % fc
        arcpy.AddField_management(fc, fieldName, "FLOAT")#Add field in all tables
        rows = arcpy.UpdateCursor(fc)
        for row in rows:
            try:
                
                row.setValue(fieldName,(row.STD / row.MEAN))#update with coefficient of variance
                
            except:
                # since this isn't being run as a script tool, we can use print instead of arcpy.AddError
                print "Unable to update row in object %s - standard deviation is %s, mean is %s" % (fc,row.STD,row.MEAN)
                continue # this will skip this iteration of the inner loop after printing the error
                
            rows.updateRow(row)
        del rows, row# Delete cursor and row objects

except:
    if not arcpy.GetMessages() == "":
        arcpy.AddMessage(arcpy.GetMessages(2))
    raise
