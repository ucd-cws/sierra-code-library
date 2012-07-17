#Calculate CT for USGS surface water discharge data#
#Author: EHolmz

#library(plyr)
#library(lattice)

#set working directory (the output location for the graph)
setwd("C:/Users/Eric/Documents/USFWS/ClimateSectionofWRIA/Climate_Data/USGS")

#Use this to quickly change the station and/or date range for the input data
station <- "11345500"  #Pit river at Canby= 11348500, NFA= 11427000, SF Pit R nr Likely= 11345500
start_date <- "1931-10-01"  #format "YYYY-MM-DD", NFA start_date = "1941-10-01"
end_date <- "2011-09-30"	#format "YYYY-MM-DD"

data <- read.table(paste("http://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&begin_date=", start_date, "&end_date=", end_date, "&site_no=", station,"&referred_module=sw", sep=""), header=F, sep="\t", skip=28)
data <- na.omit(data)

#If you already have the URL for the desired station and date range
#data <- read.table("http://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&begin_date=1904-01-01&end_date=2012-04-05&site_no=11348500&referred_module=sw", header=F ,sep="\t", skip=28)

colnames(data) <- c("agency","station","date","discharge","qualification")
data$agency <- as.character(data$agency)
data$date <- as.Date(data$date)
#data$discharge <- data$discharge*0.00138127855871

data$day <- as.numeric(format(data$date, format="%d"))
data$jday <- strptime(data$date, "%Y-%m-%d")$yday+1

data$mo <- as.numeric(format(data$date, format="%m"))
data$yr <- as.numeric(format(data$date, format="%Y"))
data$moyr <- paste(data$yr, "-", data$mo, sep="")
data$wy <- ifelse(data$mo>9,data$yr+1, data$yr)

s <- seq(1904,2012, 4)
data$tf <- data$yr %in% s

data$wyjday <- ifelse(data$tf == TRUE, ifelse(data$mo > 9, data$jday - 275, data$jday + 92), ifelse(data$mo > 9, data$jday - 274, data$jday + 92))
data$cttop <- data$wyjday*data$discharge

#str(data)
head(data)

t <- aggregate(data$cttop, by = list(data$wy), FUN = "sum")
b <- aggregate(data$discharge, by = list(data$wy), FUN = "sum")
CT <- t/b
CT$yr <- c(min(data$wy):max(data$wy))

#write.csv(CT, file="C:/Users/Eric/Documents/USFWS/ClimateSectionofWRIA/Climate_Data/USGS/write.csv")
#write.csv(data, file="C:/Users/Eric/Documents/USFWS/ClimateSectionofWRIA/Climate_Data/USGS/write.csv")

#pdf(paste("CTforPitRnrCanby",".pdf", sep=""))
plot(CT$x~CT$yr, ylab= "Day Since Start of Water Year", xlab=NA,
     main=paste("Center of Timing (CT) of Water Year Surface Runoff", "\n", "for USGS Station: ", station, sep=""))
  abline(lm(CT$x~CT$yr))
  lines(loess.smooth(CT$yr,CT$x, span = .125), col="red", lty=2)
  grid()
#dev.off()

#par(new=T)
#plot(b, yaxt="n", type="l", col="grey", xlab=NA, ylab=NA)
  #axis(4, pretty(c(0, 1.1*max(b))))
  #abline(lm(unlist(b)~CT$yr)), by = list(data$wy), FUN = "sum")
#CT <- t/b
#CT$yr <- c(min(data$wy):max(data$wy))

#cor.test(CT$x, CT$yr, alternative=c("two.sided"),method=c("kendall"),exact=NULL, conf.level = .95, continuity=FALSE)

#pdo <- read.csv("C:/Users/Eric/Documents/USFWS/ClimateSectionofWRIA/Climate_Data/Rawdata/PDO.csv",header=T)
#subset(CT
#arima(CT$x,xreg=
