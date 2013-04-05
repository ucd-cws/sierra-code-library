#########################################
## R basic functions:                  ##
## adapted from Jelmer Borst           ##
## includes functions from R. Peek     ##
## 10-02-2012                          ##

print.functions <- function(){
	cat("Rounding etc.:\n",sep="")
	cat("---------\n",sep="")
	cat("roundup(x, numdigits=0) - correct rounding of .5 etc.\n",sep="")
	cat("round.largest(x) - round to largest digit, i.e., 54 -> 50 \n",sep="")
	cat("ceiling.largest(x) - ceiling to largest digit, i.e., 54 -> 60\n",sep="")
	cat("is.odd(x) - returns TRUE if roundup(x) is an odd number\n",sep="")
	cat("is.even(x) - returns TRUE if roundup(x) is an even number\n",sep="")
	cat("get.num(x) - returns numeric values of x\n\n",sep="")


	cat("Standard errors, error bars, rmsd etc:\n",sep="")
	cat("--------------------------------------\n",sep="")
	cat("se(x) - standard error\n",sep="")
	cat("rmsd(x) - root mean squared deviation\n",sep="")
	cat("errbar(x,y,error,color=black) - plot error bars on (x,y)\n",sep="")
	cat("runmean(x,window) - running average of x with window, returns same length as x, with smoothed end points\n",sep="")
	cat("runmax(x,window) - running max of x with window, returns same length as x, with smoothed end points\n",sep="")
	cat("rollmin(x,window) - running min of x with window, edited version of rollmax from zoo package\n",sep="")
	cat("runmin(x,window) - running min of x with window, returns same length as x, with smoothed end points\n\n",sep="")


	cat("Statistics:\n",sep="")
	cat("-----------\n",sep="")
	cat("simple.partial.eta.squared(model,frame) - calculate partial eta squared for frame of anova model -- NOT ALWAYS CORRECT\n",sep="")
	cat("get.partial.etas(model) - calculate all partial eta squared's for anova model\n",sep="")
	cat("rm.levels(factor) - remove non-used levels from factor\n",sep="")
	cat("reject.z(x,index=NULL,threshold=2) - reject x's, split over index, with z > threshold\n",sep="")
	cat("make.z(x,index=NULL) - get z scores, split over index\n",sep="")
	cat("replace.z(x,index=NULL,threshold=2) - replace x's with threshold, split over index, with z > threshold\n\n",sep="")


	cat("Misc.:\n",sep="")
	cat("--------\n",sep="")
	cat("h(x,...) - shortcut for head(x,...), see ?head\n",sep="")
	cat("last(x) - get last element of vector, list, data.frame, etc.\n",sep="")
	cat("x %out% y - return T if x not in y (opposite of %in%)\n",sep="")
	cat("agg(x,index,function,name=x) - aggregate(x,index,function), name column x 'name'\n",sep="")
	cat("format.hrs.min.sec(seconds) - return hrs:min:sec or min:sec if sec < 3600\n",sep="")
	cat("performance(expr, samples=1, gcFirst=TRUE) - do 'samples' samples of function 'expr' to test its performance\n\n",sep="")
	cat("describe(x) - an alternative to summary of numeric vector or list\n",sep="")
	cat("convertBaro(x, type=) - Convert Barometric Pressures to METRIC water column equivalent\n",sep="")
	cat("instant_pkgs(c(pkg)) - instant packages for multiple package install\n",sep="")	
}

## Rounding etc.
##########################################################################################

#correct rounding of .5 etc.
roundup <- function(x,numdigits=0){
	x <- x * 10^numdigits
	x <- ifelse(x<0,-trunc(abs(x)+0.5),trunc(x+0.5))
	x / 10^numdigits
}

#round to largest 10's
round.largest <- function(x){
	x <- roundup(x)
	y <- 10^(nchar(as.character(x))-1)
	roundup(x / y) * y
}

#ceiling to largest 10's
ceiling.largest <- function(x){
	x <- roundup(x)
	y <- 10^(nchar(as.character(x))-1)
	ceiling(x / y) * y
}

#is x odd?
is.odd <- function(x){
	(roundup(x) %% 2 != 0)
}

#is x even?
is.even <- function(x){
	(roundup(x) %% 2 == 0)
}

#return numeric value of x
get.num <- function(x){
	if(is.factor(x)){
		as.numeric(as.character(x))
	}else{
		as.numeric(x)
	}
}


## Standard errors, error bars, rmsd etc:
##########################################################################################

#rmsd
rmsd <- function(data,model){
	sqrt(mean((data - model)^2))	
}

#standard error
se <- function(x){
	sd(x)/sqrt(length(x))
}

#draw error bars
errbar <- function(x,y,error,color="black"){
	arrows(x,y-error,x,y+error,angle=90,length=.05,code=3,col=color) 
}

##rolmean with smooth function
runmean <- function(x,window){
	require(zoo)
	ori <- x
	new <- rollmean(x,window,na.pad=T)
	new[is.na(new)] <- ori[is.na(new)]
	new <- smoothEnds(new,window)
	new
}

#rollmax with smooth function
runmax <- function(x,window){
	require(zoo)
	ori <- x
	new <- rollmax(x,window,na.pad=T)
	new[is.na(new)] <- ori[is.na(new)]
	new <- smoothEnds(new,window)
	new
}

#copy-pasted and edited from zoo
rollmin <- function(x, k, na.pad = FALSE, align = c("center", "left", "right"), ...)
{
  n <- length(x) 
  rval <- rep(0, n) 
  a <- 0
  for (i in k:n) {
  rval[i] <- if (is.na(a) || is.na(rval[i=1]) || a==rval[i-1]) 
      min(x[(i-k+1):i]) # calculate max of window
  else 
      min(rval[i-1], x[i]); # max of window = rval[i-1] 
  a <- x[i-k+1] # point that will be removed from window
  }
  rval <- rval[-seq(k-1)]
  if (na.pad) {
    rval <- switch(match.arg(align),
      "left" = { c(rval, rep(NA, k-1)) },
      "center" = { c(rep(NA, floor((k-1)/2)), rval, rep(NA, ceiling((k-1)/2))) },
      "right" = { c(rep(NA, k-1), rval) })
  }
  return(rval)
} 

#rollmin with smooth function
runmin <- function(x,window){
	require(zoo)
	ori <- x
	new <- rollmin(x,window,na.pad=T)
	new[is.na(new)] <- ori[is.na(new)]
	new <- smoothEnds(new,window)
	new
}


## Statistics
##########################################################################################


## Calulates the partial eta squared for the nth frame of the model. 
## NOT ALWAYS CORRECT!!
simple.partial.eta.squared <- function(model,frame) {
	ss <- summary(model)[[frame]][[1]]$"Sum Sq"
	ss[1] / (ss[1] + ss[length(ss)])
}

#calculates all eta squareds for anova model
get.partial.etas <- function(model){
	require(gdata)
	n <- names(summary(model))
	cat("\nPartial eta squared values\n",sep="")
	cat("----------------------------\n\n",sep="")
	for(idx in 1:length(n)){
		m <- row.names(summary(model)[[idx]][[1]])
		ss <- summary(model)[[idx]][[1]]$"Sum Sq"
		if(length(ss)>1){
			cat(n[idx],"\n",sep="")	
			for(j in 1:(length(m)-1)){
				eta <- ifelse(length(ss) < 2, NA, ss[j] / (ss[j] + last(ss)))
				cat(m[j],": ",eta,"\n",sep="")
			}
			cat("---\n\n",sep="")
		}
	}
}

## rm.levels(factor) - remove non-used levels from factor\n",sep="")
rm.levels <- function(factor){
	as.factor(as.character(factor))
}



#for example: with(dat,reject.z(RT,list(cond,cond2,pp),z_score)))
reject.z <- function(x,index=NULL,threshold=2) {
 if (is.null(index)) {
   index <- rep(1,length(x))
 }
 z <- rep(NA,length(x))
 
 .reject.z <- function(v,data,threshold) {
   
   d <- data[v]
   mean.d <- mean(d)
   sd.d <- sd(d)

   if (sd.d>0) {
     tmp.z <- (d - mean.d) / sd.d

     z[v] <<- d
     z[v][abs(tmp.z)>threshold] <<- NA
   }
   
   return(NULL)
 }
 tapply(1:length(x),index,.reject.z,x,threshold)

 z
}

make.z <- function(x,index=NULL) {
 if (is.null(index)) {
   index <- rep(1,length(x))
 }
 z <- rep(NA,length(x))
 
 .make.z <- function(v,data) {
   d <- data[v]
   z[v][sd(d)>0] <<- (d - mean(d)) / sd(d)[sd(d)>0]
   return(NULL)
 }
 tapply(1:length(x),index,.make.z,x)
 z
}

replace.z <- function(x,index=NULL,threshold=2) {
 if (is.null(index)) {
   index <- rep(1,length(x))
 }
 z <- rep(NA,length(x))
 
 .replace.z <- function(v,data,threshold) {
   
   d <- data[v]
   mean.d <- mean(d)
   sd.d <- sd(d)

   if (sd.d>0) {
     ma <- mean.d + (threshold * sd.d)
     mi <- mean.d - (threshold * sd.d)
     tmp.z <- (d - mean.d) / sd.d

     z[v] <<- d
     z[v][tmp.z>threshold] <<- ma
     z[v][tmp.z<(-1*threshold)] <<- mi
   }
   
   return(NULL)
 }
 tapply(1:length(x),index,.replace.z,x,threshold)
 z
}

## Misc
##########################################################################################

#shortcut for head: see ?head
h <- function(data, ...){
	head(data, ...)
}

#get last element of list, vector, etc
last <- function(x){
	x[length(x)]
}

#return TRUE for items not in y, opposite of %in%
"%out%" <- function(x,y){
	!(x %in% y)
}

#aggregate with 'naming the x'
agg <- function(x,index,fun,name="x"){
	tmp <- aggregate(x,index,fun)
	names(tmp)[ncol(tmp)] <- name
	tmp
}

#get hrs:min:sec from seconds
format.hrs.min.sec <- function(seconds){
	minutes <- seconds / 60
	if(minutes >= 60){
		hrs <- trunc(seconds / 3600)
		paste(hrs,":",sprintf("%02.0f",trunc(minutes) - (60*hrs),2),":",sprintf("%02.0f",roundup((minutes - trunc(minutes)) * 60,2)),sep="")
	}else{
		paste(trunc(minutes),":",sprintf("%02.0f",roundup((minutes - trunc(minutes)) * 60,2)),sep="")
	}
}

#do 'samples' samples of function 'expr' to test its performance
performance <- function(expr, samples=1, gcFirst=TRUE){

	loc.frame <- parent.frame()
	results <- data.frame()
     
	for(i in 1:samples){
		if (gcFirst){ gc(FALSE) }
		expr <- substitute(expr)
    	time <- proc.time()
		eval(expr, envir = loc.frame)
    	new.time <- proc.time()
    	results <- rbind(results,as.vector(structure(new.time - time, class = "proc_time"))[1:3])
	}   
    
	test <<- results
	cat("\n\tAverage time per run:\n\t---------------------\n")
	cat("\tUser\t\tSystem\t\tElapsed\n")
	cat("\t",format(roundup(mean(results[1]),3),nsmall=3),"\t\t",format(roundup(mean(results[2]),3),nsmall=3),"\t\t",format(roundup(mean(results[3]),3),nsmall=3),sep="")
	
	cat("\n\n\tTotal time for all runs:\n\t------------------------\n")
	cat("\tUser\t\tSystem\t\tElapsed\n")
	cat("\t",format(roundup(sum(results[1]),3), nsmall=3),"\t\t",format(roundup(sum(results[2]),3),nsmall=3),"\t\t",format(roundup(sum(results[3]),3),nsmall=3),sep="")
	cat(" \n ")

}

#an alternative to summary of numeric vector or list
describe <- function(x){
    m=mean(x,na.rm=T)
    s=sd(x,na.rm=T)
    N=sum(is.na(x))
    n=length(x)-N
    se=s/sqrt(n)
    out=c(m,s,se,n,N)
    names(out)=c("mean","sd","sem","n","NAs")
    round(out,4)
}

#convert barometric pressures to METRIC water column equivalent
convertBaro <- function(x, type){ 
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
	return(x)
}

#instant packages for multiple package install
 instant_pkgs <- function(pkgs) { 
    pkgs_miss <- pkgs[which(!pkgs %in% installed.packages()[, 1])]
    if (length(pkgs_miss) > 0) {
        install.packages(pkgs_miss)
    }
    
	if (length(pkgs_miss) == 0) {
	message("\n ...Packages were already installed!\n")
	}

    # install packages not already loaded:
    pkgs_miss <- pkgs[which(!pkgs %in% installed.packages()[, 1])]
    if (length(pkgs_miss) > 0) {
        install.packages(pkgs_miss)
    }
    
    # load packages not already loaded:
    attached <- search()
    attached_pkgs <- attached[grepl("package", attached)]
    need_to_attach <- pkgs[which(!pkgs %in% gsub("package:", "", attached_pkgs))]
    
    if (length(need_to_attach) > 0) {
      for (i in 1:length(need_to_attach)) require(need_to_attach[i], character.only = TRUE)
    }

	if (length(need_to_attach) == 0) {
	message("\n ...Packages were already loaded!\n")
	}
}