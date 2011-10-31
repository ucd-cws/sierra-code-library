from common import *
import os

debug = False #original code being built on uses a debug variable, so we'll define it here

# style: lowercase with underscores for all variable names,
#    camel case with cap first for all functions (consistent with arcpy)
#    file split: by major task

bcm_data = ''

args_defs = {'meadows_fc': 0,'output_fc': 1}

def GetArgs(num_args):
    
    l_args = []
    
    for i in range(num_args):
        l_args.append(arcpy.GetParameterAsText(i))

    return l_args()


location = None
spatial_data = None # location of spatial data folder
output = None # location of all output
flow_direction_raster = None
flow_accumulation_raster = None
temp_gdb = None

## possibly have geodatabases for caching watershed level clips of these items
#fdir_cache = None
#facc_cache = None 
#use_cache = True

def SetUpEnvironment():
    try:
        global location, spatial_data, output, flow_direction_raster,flow_accumulation_raster,temp_gdb
        
        location = os.getcwd() # initialize the location to here
        location = os.chdir("..") # move up one directory

        spatial_data = os.path.join(location, "spatial")
        output = os.path.join(location, "output")
        
        flow_direction_raster = os.path.join(spatial_data,"SN_DEM.gdb","flow_dir_final") 
        flow_accumulation_raster = os.path.join(spatial_data,"SN_DEM.gdb","flow_acc_final")
        temp_gdb = os.path.join(spatial_data,"temp.gdb")
        
        try:
            #arcpy.env.workspace = output_data_dir
            #arcpy.env.scratchworkspace = "E:/TEMP/"
            #arcpy.env.pyramid = "NONE"
            #arcpy.env.rasterstatistics = "NONE"
            #if (debug): print "Workspace: " + (gp.Workspace)
            #if (debug): print "FDir: %s" % (dem_fdir)
            #if (debug): print "Points: %s" % (sample_points)
            pass
        except:
            raise FatalError("Error Setting up Environment")

    except FatalError: # if we get a more specific error, raise it instead
        raise
    except:
        raise FatalError("no environment")