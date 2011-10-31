import arcpy, os
import vars, funcs, log

try:
    from _winreg import *
    registry = ConnectRegistry("",HKEY_CURRENT_USER) # open the registry
    base_folder = QueryValue(registry,"Software\CWS\PISCES\location") # get the PISCES location
    CloseKey(registry)
except:
    log.error("Unable to get base folder")
    sys.exit()

vars.set_workspace_vars(base_folder) # set up the workspace to the location

log.initialize("tbx_add_alt_codes starting",arc_script = 1)
import script_tool_funcs

arcpy.env.overwriteOutput = True # we want to overwrite outputs because we'll be writing to temp.mdb

feature_layer = arcpy.GetParameterAsText(0)
column = arcpy.GetParameterAsText(1)
input_filter = arcpy.GetParameterAsText(2)
fid_column = arcpy.GetParameterAsText(3)
if fid_column == "":
    fid_column = None


class alt_code(): # def the class - it'll be used when retrieving the results
    def __init__(self, l_code = None, l_fid = None):
        self.fid = l_fid
        self.input_filter = input_filter # auto set it to the global input_filter
        self.alt_code = l_code

all_codes = [] # holds the retrieved codes

log.write("Retrieving information from feature")

new_features = os.path.join(vars.workspace,feature_layer)

# Copy features to temp.mdb so we can sql over it
arcpy.CopyFeatures_management(feature_layer,new_features)

db_cursor,db_conn = funcs.db_connect(vars.workspace, "retrieving info from calcs db on alt_codes")

l_sql = "" # init it to empty so that it gets overridden in the blocks
if fid_column is None: # the general case is that we don't have an fid_column
    l_sql = "select distinct %s as Identifier from %s" % (column,feature_layer)
else:
    l_sql = "select distinct %s as Identifier, %s as Fid from %s" % (column,fid_column,feature_layer)

log.write(l_sql)

l_codes = db_cursor.execute(l_sql)
for code in l_codes:
    l_alt = alt_code(code.Identifier)
    if fid_column is not None:
        l_alt.fid = code.Fid
    all_codes.append(l_alt)

funcs.db_close(db_cursor,db_conn)# close the temp db
del l_codes # get rid of the results explicitly

log.write("Updating database with information")

db_cursor,db_conn = funcs.db_connect(vars.maindb,"inserting alt codes from script tool")

l_sql = "insert into Alt_Codes (FID,Alt_Code,Input_Filter) values (?,?,?)"
for l_code in all_codes: # insert the codes
    db_cursor.execute(l_sql,l_code.fid,l_code.alt_code,l_code.input_filter)

db_conn.commit()
arcpy.Delete_management(new_features) # cleanup

arcpy.AddWarning("Alt_Codes added for input filter %s - be sure to go check and add any necessary and missing FIDs for the codes" % input_filter)

# get feature layer
# copy it to temp.mdb so we can sql it
# run the sql to get the unique values
# delete from temp.mdb
# insert records into alt_codes
# save records
# AddMessage that it's complete and that user needs to go add FIDs'