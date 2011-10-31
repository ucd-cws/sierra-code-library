import arcpy, sys, os
import string



def remove_dataset(set_id,invalidate=1):

	if invalidate == 1: # if we just want to invalidate the whole set, not nuke it into oblivion
		import modify_records
		modify_records.invalidate_records("Set_ID = %s" % set_id)
	else: # we want it gone
		query1 = "delete from Observation_Sets where Set_ID = ?"
		query2 = "delete from Observations where Set_ID = ?"
		
	