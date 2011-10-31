import sys
import arcpy
import config

class FatalError(Exception):
    def __init__(self, value=""):
        log(str(value),1)
        
    log("Unrecoverable Exception raised. Exiting",1)
    sys.exit()

class watershed():
    '''Used for defined watersheds (things like WEAP or HUCs)'''
    def __init__(self):
        self.name = None
        self.id = None
        self.spatial = None
        
class local_watershed():
    '''Used for generated watersheds, the contributing area to a given point, etc'''
    def __init__(self):
        pass

def log(msg,auto_print = 0):
    # leaves room for a file write
    if auto_print == 1:
        print msg
        
        
# ----------------------------------------------------------------------------
#  Get Raster Properties
#    input_raster: Raster to determine property
#    property: one of - MINIMUM, MAXIMUM, MEAN, STD, UNIQUEVALUECOUNT,
#       TOP, LEFT, RIGHT, BOTTOM, CELLSIZEX, CELLSIZEY, VALUETYPE
#       COLUMNCOUNT, ROWCOUNT, BANDCOUNT
# ----------------------------------------------------------------------------
def get_raster_property(input_raster, property):
    try:
        if (config.debug): print "Getting raster property: " + property
        value = arcpy.GetRasterProperties_management(input_raster, property)
        print value
        return value

    except:
        print arcpy.AddMessage("Error getting raster property: " + property)
        sys.exit(0)
