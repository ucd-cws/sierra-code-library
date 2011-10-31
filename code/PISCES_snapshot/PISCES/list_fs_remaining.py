import vars, funcs, log

log.initialize("Just getting a listing!")

db_cursor, db_conn = funcs.db_connect(vars.maindb, "retrieving species remaining to QC")

query = "select Species.FID, Species.Common_Name from Species, Species_Aux where Species_Aux.FS_Sensitive_Status = True and Species.FID = Species_Aux.FID"
results = db_cursor.execute(query)

file = open("outfile.log",'w')

num_results = 0
for result in results:
	log.write("\nFID %s, %s is a FSSC" % (result.FID,result.Common_Name), 1)
	l_cursor = db_conn.cursor()
	l_query = "select count(*) as l_count from observations where Species_ID = ? and (IF_Method = 9 or IF_Method = 10)"
	l_results = l_cursor.execute(l_query, result.FID)
	
	for ls_result in l_results:
		log.write("Number of MKS results %s" % ls_result.l_count, 1)
		if ls_result.l_count < 1:
			log.write("%s Needs attention!!\n\n" % result.FID, 1)
			file.write(result.FID)
			file.write("\n")
			
	num_results = num_results + 1
	
print "total results: %s" % num_results
			
funcs.db_close(db_cursor,db_conn)