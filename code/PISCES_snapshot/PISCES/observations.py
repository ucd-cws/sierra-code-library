import arcpy
import os
import vars, log, funcs

observation_certainties = {}

def get_observation_certainties():
    global observation_certainties
    
    db_cursor,db_conn = funcs.db_connect(vars.maindb)
    
    l_sql = "select Type, Default_Certainty from defs_Observation_Types order by Type"
    l_results = db_cursor.execute(l_sql)
    
    for result in l_results:
        observation_certainties[result.Type] = result.Default_Certainty
    
    funcs.db_close(db_cursor, db_conn)

def check_observations_db():
    try:
        if not arcpy.Exists(vars.observationsdb):
            obs_db = os.path.split(vars.observationsdb)
            arcpy.CreateFileGDB_management(obs_db[0],obs_db[1])
    except:
        log.write(auto_print=1,log_string="Unable to check on existence of observations geodatabase or create new database")
        raise  

