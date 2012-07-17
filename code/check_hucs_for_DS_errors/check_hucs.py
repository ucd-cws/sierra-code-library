import arcpy

huc_curs = arcpy.SearchCursor(r"C:\Users\nicksantos\Documents\PISCES\data\geo_aux.mdb\HUC12_Western_US")

i=0

network_end_hucs = ["CLOSED BASIN","Mexico","OCEAN"]

huc12s = []
huc10s = []
marked_as_bad = []

for row in huc_curs:
	huc12s.append(row.getValue("HUC_12"))
	huc10s.append(row.getValue("HUC_10"))

del huc_curs

# reload the cursor
huc_curs = arcpy.SearchCursor(r"C:\Users\nicksantos\Documents\PISCES\data\geo_aux.mdb\HUC12_Western_US")	

query_out = open("query_out.txt",'w')
problem_out = open("problem_out.txt",'w')

nonexistent_query_out = open("nonexistent_query_out.txt",'w')
nonexistent_problem_out = open("nonexistent_problem_out.txt",'w')

hu10_query_out = open("huc10_query_out.txt",'w')
hu10_problem_out = open("huc10_problem_out.txt",'w')

for row in huc_curs:
	i += 1
	#if i % 100 == 0:
	#	print i
	if not row.getValue("HUC_12"):
		continue
		
	if row.getValue("HU_12_DS") not in huc12s and row.getValue("HU_12_DS") not in network_end_hucs:
		marked_as_bad.append(row.getValue("HUC_12"))
		nonexistent_query_out.write("\"HUC_12\" = '%s' OR \n" % row.getValue("HUC_12"))
		nonexistent_problem_out.write("HU_12_DS for %s specifies a HUC_12 that doesn't exist in this dataset\n" % row.getValue("HUC_12"))
		
	if row.getValue("HU_10_DS") not in huc10s and row.getValue("HU_10_DS") not in network_end_hucs:
		marked_as_bad.append(row.getValue("HUC_12"))
		hu10_query_out.write("\"HUC_12\" = '%s' OR \n" % row.getValue("HUC_12"))
		hu10_problem_out.write("HU_10_DS for %s specifies a HUC_10 that doesn't exist in this dataset\n" % row.getValue("HUC_12"))
		
	if row.getValue("HUC_10") not in row.getValue("HU_12_DS") and row.getValue("HU_10_DS") not in row.getValue("HU_12_DS"):
		query_out.write("\"HUC_12\" = '%s' OR \n" % row.getValue("HUC_12"))
		problem_out.write("HU_12_DS for %s is not within the current HUC_10 or the downstream HUC_10 - possible problem with any of the involved attributes\n" % row.getValue("HUC_12"))
		
	
		
