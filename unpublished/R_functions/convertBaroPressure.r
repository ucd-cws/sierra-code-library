##Convert Barometric Pressures to METRIC water column equivalent:

convertBaroPressure<-function(x, type){ 
	if(type == "in") {
	x <-(x * 0.3453) - 9 
	} else {
	if(type == "mm"){
	x <-(x * 0.01362)
	} else {
	if(type== "psi") {
	x <-(x * 0.7043)
	} else {
	if(type== "kPa") {
	x <-(x * 0.1022)
	} else {
	if(type== "atm") {
	x <-(x * 10.351) 
	}
	}}}}
	#result <- list(x,cat(type,"to meters","\n"))
	#return(result)
	return(x)
	}

	