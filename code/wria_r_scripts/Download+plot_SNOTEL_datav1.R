#Read NRCS SNOTEL climate data from website in tab delimited format
#Created by E. Holmes

library(lattice)
#Set working directory, and will be the location of the output graphs
setwd("C:/Users/Eric/Documents/USFWS/ClimateSectionofWRIA/Climate_Data/NRCS/output")
			
#read data table from the NRCS SNOTEL site and store as a new dataframe 'data'.  Header is TRUE, and the data is tab separated
data <- read.table("http://www.wcc.nrcs.usda.gov/ftpref/data/snow/snotel/cards/california/20h06s_all.txt", header=T ,sep="\t")		

#stores the column names from the 'data' dataframe
w <- colnames(data)
														
#stores the site name with the ".data" trimmed off the end
sitename <- substr(w[1], 1, nchar(w[1])-5)										
d <- data[[w[1]]]														

#a new R object is created using a logical statement which converts the NRCS date format to a text string which can be understood by R
f <- ifelse(nchar(d)<6, paste(substr(d,4,5), "-", substr(d, 2, 3), "-", substr(d, 0, 1), sep=""), 	
	paste(substr(d,5,6), "-", substr(d, 3,4), "-", substr(d, 1,2), sep=""))

#takes the R object 'f', converts it to the native R date format, and adds it as a new column to the 'data' dataframe
data$date <- as.Date(f, "%y-%d-%m")	

#creates new columns in the 'data' dataframe which inlcude the numeric month, numeric year, year-month, and numeric water year											
data$mo <- as.numeric(format(data$date, format="%m"))									
data$yr <- as.numeric(format(data$date, format="%Y"))
data$moyr <- paste(data$yr, "-", data$mo, sep="")
data$wy <- ifelse(data$mo>9,data$yr+1, data$yr)

#prints to the R console the first column heading s and first five data rows to check if data was read in correctly
head(data)																

#creates a subset of the 'data' dataframe																
ds <- subset(data, data$date>("1980-09-30") & data$date<("2010-10-01"))
						
#replaces all NAs with 0s in the ds$prcp column
ds$prcp[is.na(ds$prcp)] <-0	
												
#creates a new data object with the NAs omitted (omits entire row when an NA is encountered)
new.data <- na.omit(data)
													
#creates an new object 'pag' with computed monthly precipitation sums for each month of each year
pag <- aggregate(ds$prcp, by = list(ds$moyr), FUN = "sum")								
  pag$yr <- substr(pag$Group.1, 1, 4)											#adds a year column to the 'pag' object
  pag$mo <- as.numeric(ifelse(nchar(pag$Group.1)<7, substr(pag$Group.1, 6,6), 				#adds a month column to the 'pag' object
	substr(pag$Group.1, 6, 7)))

#creates a new object 'pagavg' with the monthly sums averaged over the number of years of data 
pagavg <- aggregate(pag$x, by = list(pag$mo), FUN = "mean")								

pwy <- aggregate(ds$prcp, by = list(ds$wy), FUN = "sum")
p <- pwy$x
wy <-pwy$Group.1

#tag <- aggregate(new.data$tavg, by = list(new.data$moyr), FUN = mean)
tavg <- aggregate(new.data$tavg, by = list(new.data$mo), FUN = "mean")						#computes monthly mean of daily average temperature
tmin <- aggregate(new.data$tmin, by = list(new.data$mo), FUN = "mean")
tmax <- aggregate(new.data$tmax, by = list(new.data$mo), FUN = "mean")


pdf(paste(sitename, "_", "total_WY_precip", ".pdf", sep=""))
barchart(p ~ wy, 
	horizontal=FALSE, 
	ylim=c(0,max(p)),
	main=paste("NRCS SNOTEL SITE:", sitename, "\n","Total Water Year Precipitation", sep=""),
	ylab="Precipitation (inches)",
	xlab=NULL,
	scales=list(x = list(at = 1:30, labels = wy, rot=90), y="free"),
	col="blue")
dev.off()

#pdf(paste(sitename, "_", "accum_precip", ".pdf", sep=""))								#creates and names an output pdf
  plot(ds$prec~ds$date, type="l",lty=1, main=paste("NRCS SNOTEL SITE:",sitename, 				#plot accumulated precipitation
	"\n", "Water Year Accumulated Precipitation"), ylab="Precipitation (inches)", xlab="Year")
    grid()
    mtext(paste(min(ds$date), "to", max(ds$date)), line=-1, cex=.75)
  #dev.off()

#pdf(paste(sitename, "_", "avg_monthly_precip", ".pdf", sep=""))
  boxplot(pag$x~pag$mo, main=paste("NRCS SNOTEL SITE:", sitename, "\n", 					#boxplot average monthly precipitation
	"Average Monthly Precipitation"), ylab="Precipitation (inches)", xlab="Month", col="blue") 								 
    lines(pagavg)
    grid()
    mtext(paste(min(ds$date), "to", max(ds$date)), line=-1, cex=.75)
    legend("topleft", c("Mean"), col=("black"), lty=1)
  #dev.off()

#pdf(paste(sitename, "_", "avg_monthly_temp", ".pdf", sep=""))
  #plot monthly average temperature with monthly average highs and lows shown as lines
  boxplot(new.data$tavg~new.data$mo, main=paste("NRCS SNOTEL SITE:", sitename, "\n", 			
	"Average Monthly Temperature"), ylab="Temperature (Celsius)", xlab="Month", ylim=c(-15,30))
    lines(tmin, col="blue")
    lines(tmax, col="red")
    lines(tavg)
    grid()
    legend("topleft", c("Max", "Mean", "Min"), col=c("red", "black", "blue"), lty=1)
    mtext(paste(min(new.data$date),"to", max(new.data$date)),3,line=-1, cex=.75)
  #dev.off()

#creates a preview of the output graphs in a two by two plot matrix in an active device which is filled with subsequent plots
par(mfrow=c(2,2))															

 #barchart(p ~ wy, 
	#horizontal=FALSE, 
	#ylim=c(0,max(p)),
	#main=paste("NRCS SNOTEL SITE:", sitename, "\n","Total Water Year Precipitation", sep=""),
	#ylab="Precipitation (inches)",
	#xlab=NULL,
	#scales=list(x = list(at = 1:30, labels = wy, rot=90), y="free"))

  #plot accumulated precipitation  
  plot(ds$prec~ds$date, type="l",lty=1, main=paste("NRCS SNOTEL SITE:",sitename, 				
	"\n", "Water Year Accumulated Precipitation"), ylab="Precipitation (inches)", xlab="Year")
    grid()
    mtext(paste(min(ds$date), "to", max(ds$date)), line=-1, cex=.75)
  
  #boxplot average monthly precipitation
  boxplot(pag$x~pag$mo, main=paste("NRCS SNOTEL SITE:", sitename, "\n", 					
	"Average Monthly Precipitation"), ylab="Precipitation (inches)", xlab="Month", col="blue") 								 
    lines(pagavg)						#adds a line depicting the monthly precipitation means calculated in 'pagavg'
    grid()							#adds a grid to the plot
    legend("topleft", c("Mean"), col=("black"), lty=1)
    mtext(paste(min(ds$date), "to", max(ds$date)), line=-1, cex=.75)						

  #plot monthly average temperature with monthly average highs and lows shown as lines
  boxplot(new.data$tavg~new.data$mo, main=paste("NRCS SNOTEL SITE: ", sitename, "\n",			
	"Average Monthly Temperature",sep=""), ylab="Temperature (Celsius)", 
	xlab="Month", ylim=c(-15,30))					
    lines(tmin, col="blue")
    lines(tmax, col="red")
    lines(tavg)
    grid()
    legend("topleft", c("Max", "Mean", "Min"), col=c("red", "black", "blue"), lty=1)
    mtext(paste(min(new.data$date),"to", max(new.data$date)),3,line=-1, cex=.75) 
  #par(new=TRUE)
    #boxplot(new.data$tavg~new.data$mo)    
    #boxplot(new.data$tmin~new.data$mo, col="blue", axis=FALSE, pch=4,ylim=c(-20,35))
    #lines(tavg)
  #par(new=TRUE)
    #boxplot(new.data$tmax~new.data$mo, col="red", pch=2, ylim=c(-20,35))

