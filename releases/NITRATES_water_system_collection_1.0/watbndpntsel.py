# ---------------------------------------------------------------------------
# watbndpntsel.py
# Created on: 2011-02-16 11:55:35.00000
# Usage: bufferpntsel <pnts> <polys> <output>
# Description:
# Selects Points from larger shapefile by FID and creates a feature class
# Runs each feature class through the Buffer Iteration
# Stops after sum population of dissolved census block selection exceeds point population

# ---------------------------------------------------------------------------

# Import arcpy module
import sys, os, arcpy
from arcpy import *
from time import *
# Script Debugging -- show progress messages to standard output
debug = 1

# Script arguments
### pnts = arcpy.GetParameterAsText(0)
pnts = r"E:\Nitrates\Water_System_Boundary_Collection\Model\Test_Water_Systems.shp"

###polys = arcpy.GetParameterAsText(1)
cpolys = r"E:\Nitrates\Water_System_Boundary_Collection\Model\Census_Blocks_2000.shp"

# Set the workspace
###wkspace = arcpy.GetParameterAsText(2)
wkspace = r"E:\Nitrates\Water_System_Boundary_Collection\Model\Scratch.mdb"
env.workspace = wkspace

def pnt_select(pnt, polys, outlyrname):
    try:
        if (debug): print "Selecting Point"
        arcpy.SelectLayerByLocation_management(polys, "INTERSECT", pnt)
        arcpy.MakeFeatureLayer_management(polys, outlyrname)
        return outlyrname
    except:
        print "Error Selecting Parcel Poly 1: " + outlyrname
        raise
        # If an error occurred, print line number and error message
        #import traceback, sys, os
        #tb = sys.exc_info()[2]
        #print "Line %i" % tb.tb_lineno
        #print e.message
        #sys.exit()

    
# needs to be implemented next
def poly_popncheck(polys):
    try:
        if (debug): print "Summing Poly Popn"
        ###arcpy.SelectLayerByLocation_management(polys, "INTERSECT", pnt)
        ###arcpy.MakeFeatureLayer_management(polys,outlyrname)
        return popn

    except:
        raise
        print "Error Selecting Parcel Poly 2: " + outlyrname
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)

def poly_addselect(p_poly, outlyrname, polys, selection_type):
    try:
        if (debug): print "Selecting More Polys"
        arcpy.SelectLayerByLocation_management(polys, "BOUNDARY_TOUCHES", p_poly, "#", selection_type)
        arcpy.MakeFeatureLayer_management(polys, outlyrname)
        return outlyrname

    except:
        raise
        print "Error Selecting Parcel Poly 3: " + outlyrname
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)

def export_poly(it_poly, outpath, outname):
    try:
        export_name = outpath+"\\"+outname
        print export_name

        if arcpy.Exists(export_name):
            arcpy.Delete_management(export_name)
            
        if (debug): print "Exporting adj polys to workspace"
        x_polys = arcpy.CopyFeatures_management(it_polys, export_name)
        return x_polys
    except:
        raise
        print "Error exporting adj Parcel Polys: " + outname
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)



def add_field(datasrc, fieldname, type):
    try:
        if (debug): print "Adding Field: " + fieldname
        arcpy.AddField_management(datasrc, fieldname, type)
    except:
        raise
        print "Error Selecting adding field: "
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)
# ----------------------------------------------------------------------------
#  fill field to datasource given fieldname and value
# ----------------------------------------------------------------------------
def fill_field(datasrc, fieldname, value):
    try:
        if (debug): print "Calculating Field: " + fieldname
        arcpy.CalculateField_management(datasrc, fieldname, value)
    except:
        raise
        print "Error filling field for Poly: " + datasrc
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)

# ----------------------------------------------------------------------------
#  Dissolve datasource based on fieldname
# ----------------------------------------------------------------------------
def dissolve_layer(datasrc, fieldname, indx):
    try:
        if (debug): print "Dissolving Layer: " + indx
        if arcpy.Exists("wbpk"+indx):
            arcpy.Delete_management("wbpk"+indx)
        f_polyname = "wbpk"+indx
        f_summary = [["Pop", "SUM"]]
        arcpy.Dissolve_management(datasrc, f_polyname, fieldname, f_summary, "MULTI_PART")
        return (f_polyname)

    except:
        raise
        print "Error dissolving Poly: " + datasrc
        # If an error occurred, print line number and error message
        import traceback, sys, os
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
        os.system("pause") # wait until the any key is pressed
        sys.exit(0)
# ----------------------------------------------------------------------------
#   Main - Start program
# ----------------------------------------------------------------------------
timeStart = localtime()
if (debug): print "milking machine, now started at " + strftime('%a, %d %b %Y %H:%M:%S %Z', timeStart)

# add in loop to check all inputs
try:
    polys = "poly1"
    arcpy.MakeFeatureLayer_management(cpolys, polys)
    if (debug): print "Created layer of polys"

except:
    print 'no poly layer'
    raise
  #  sys.exit(0)

# Create Cursor Container
pRecs = arcpy.SearchCursor(pnts)

for pRec in pRecs:
    
    p = pRec.System_No
    p = str(p)
    p = p[:-2]
    if (debug): print "Processing Point: " + str(p)

    if arcpy.Exists(wkspace + "\\xp"+str(p)):
        print "skipping completed fc"
        continue

    sql = "System_No = %s" % p
    print sql
    pnt = "pnt%s" % p
    arcpy.MakeFeatureLayer_management(pnts, pnt, sql)
    if (debug): print "Selected: " + sql


    try:
        p_poly = pnt_select(pnt, polys, "p_poly"+str(p))
        print 'selected prime poly' + str(p)
    except:
        print 'unable to select prime poly ' + str(p)
        raise

    #Population Check - are we at the population level that lets us stop yet?
    t_pop = 0
    it_polys = p_poly # set it_polys to p_poly so that we can keep looping through it over it_polys to grow the selections
    selection_type = "NEW_SELECTION"
    while t_pop < pRec.Population:
        print "Current population selected %i - Need to get to %i" % (t_pop,pRec.Population)
        
        try:
            it_polys = poly_addselect(it_polys, "it_poly"+str(p)+"_"+str(t_pop)+ str(time()), polys,selection_type)
            selection_type = "ADD_TO_SELECTION" # after we've gone once with new selection, we want to add to the current selection
            print 'added some adjacent polys ' + str(p)
        except:
            print 'unable to add adjacent polys'
            print it_polys
            print "it_poly"+str(p)+"_"+str(t_pop)
            print polys
            print selection_type
            raise
            
        try:
            print 'getting the population of the selection in %s' % it_polys
            l_poly = arcpy.SearchCursor(it_polys)
            for poly in l_poly:
                t_pop = t_pop + poly.Pop
        except:
            print 'unable to get the population of the selection'
		
    try:
        x_polys = export_poly(it_polys, wkspace, "xp"+str(p))
        print 'exported polys'
    except:
        print 'unable to export adjacent polys'
    try:
        add_field(x_polys, "Pkey", "TEXT")
        print 'added field to ' + str(p)
    except:
        print 'unable to add field to '+ str(p)
    try:
        fill_field(x_polys, "Pkey", p)
        print 'added and calculated field' + str(p)
    except:
        print 'unable to fill field to ' + str(p)
    try:
        f_poly = dissolve_layer(x_polys, "Pkey", str(p))
        print 'dissolved ' + str(p)
    except:
        print 'unable to dissolve'

    print "wooooohooooo! %s is analyzed - total pop = %s" % (p,t_pop)
##    if i == 1:
##        try:
##            gp.copyfeatures_management(watershed, output_watshp)
##            print 'copied feature' + str(i)
##        except:
##            print 'unable to copy feature' + str(i)
##    else:
##        try:
##            gp.Append_management(watershed, output_watshp, "NO_TEST")
##            print 'appended feature' + str(i)
##        except:
##            print 'unable to append feature ' + str(i)


timeEnd = localtime()
print '______________________________________________________________________'
print 'process started at: '+ strftime('%a, %d %b %Y %H:%M:%S %Z', timeStart)
print '  process ended at: '+ strftime('%a, %d %b %Y %H:%M:%S %Z', timeEnd)

### Process: Dissolve
##arcpy.Dissolve_management(Census_Blocks_2000__3_, v_Name__Census_Selection_Dissolve_n_, "", "Pop SUM", "MULTI_PART", "DISSOLVE_LINES")
##
### Process: Get Field Value (2)
##arcpy.GetFieldValue_mb(v_Name__Census_Selection_Dissolve_n_, "SUM_Pop", "Double", "0")
##
### Process: Calculate Value
##arcpy.CalculateValue_management("int(%CenPop%) >= int(%PointPop%)", "", "Variant")
##
