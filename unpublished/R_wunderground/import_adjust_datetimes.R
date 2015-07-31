## IMPORT ZIPPED WUNDERGROUND DATA AND ADJUST TO DATETIMES
## ALSO CONVERT TEMPS FROM US to METRIC
# R.PEEK
# 03-Oct-2012

######## FUNCTION TO ROUND TIMES TO 15 MIN ################################

snap15 <- function( x ) { 
  x <- as.POSIXlt( x + as.difftime( 15, units="mins" ) ) 
  x$sec <- 0 
  x$min <- 15*(x$min %/% 15) 
  as.POSIXct(x) 
}

######### END OF FUNCTION ##################################################

## Names used for files
site<-"Clavey_solinst_Wundr_mrg_2012"
station<-"KCAGROVE6_2012"

# Import WUNDERGROUND DATA----------------------------------------------------

# set to working directory where input files are
setwd( "C://Users//rapeek//Dropbox//R//wunderground//download")
files.gz<-list.files(pattern=".gz")
files.csv<-list.files(pattern=".csv")

# IMPORT ZIPPED WUNDERGROUND -------------------------------------------------
wunder<-read.csv(file=gzfile(files.gz),header=TRUE,as.is=TRUE)

# IMPORT UNZIPPED WUNDERGROUND -----------------------------------------------
#wunder<-read.csv('KCAGROVE6.csv', header=TRUE, as.is=TRUE)

colnames(wunder)
str(wunder)

# SELECT COLUMNS AND CONVERT DATETIMES
require(lubridate)
wunder$datetime<-ymd_hms(wunder$Time) # Convert to POSIXct 
wunder.df<-data.frame(wunder[,c(14,2,3,4,6,9,10,13)]) # select columns of interest
str(wunder.df) 

# RUN FUNCTION ON WUNDERGROUND DATA ---------------------------------------
wunder.df$time15<-snap15(wunder.df$datetime) # snap to nearest 15 min
head(wunder.df)
str(wunder.df)
wunder.df[c(1:30),c(1,9)] # visual check to make sure time stamps line up

# CONVERT F to C ----------------------------------------------------------
require(weathermetrics)
names(wunder.df)
wunder.df$ATemp_C<-with(wunder.df, fahrenheit.to.celsius(TemperatureF))
wunder.df$RH<-with(wunder.df, dewpoint.to.humidity(t=ATemp_C,dp=DewPt_C,temperature.metric="celsius"))
#wunder.df$DewPt_C<-with(wunder.df, fahrenheit.to.celsius(DewpointF))
#wunder.df$BaroStage_m<-convertBaro(wunder.df$PressureIn, type="in") # convert to metric stage
str(wunder.df)
colnames(wunder.df)
wunder.df<-wunder.df[,c(9,4,6,7,8,10,11)]

# IMPORT FLOW TEMP DATA TO MERGE-------------------------------------------
y <- read.csv("C://Users//rapeek//Dropbox//R//data//spring_recsn//loggers//2012_Clavey_solinst_compensated.csv",as.is=TRUE,skip=22,header=TRUE)
z <- read.csv("P://Public//R_Wunderground//field_data//2012_Clavey_solinst_compensated.csv.csv",as.is=TRUE,skip=1,header=TRUE)
str(y)
head(y)
#df<-data.frame(subset(colnames(y[,c(1:3)]) # select data for HOBO
#df<-y[,(grep("date|datetime|temp",colnames(y)))] # select data for HOBO
#colnames(df)<-c("X","datetimes","temp") # may need to rename columns for HOBO
df<-y[,(grep("Date|Time|LEVEL$|TEMPERATURE",colnames(y)))] # select data for solinst

df$datetime<-paste(df$Date," ",df$Time,sep="")
df$datetimes<-mdy_hms(df$datetime)

## create column for merge
df$time15<-as.POSIXct(df$datetimes, format="%m/%d/%y %I:%M:%S %p") # convert AM/PM if needed
df$time15[1:30] # quick preview of timestamps, make sure in 15 min intervals
#readline("In 15 min data intervals, YES? <ENTER>")
colnames(df)

## subset to necessary columns
logger.df<-df[,c(7,3,4)]
colnames(logger.df)<-c("time15","stage_m","WTemp_C")
head(logger.df)

# MERGE WUNDERGROUND DATA WITH TEMP DATA ----------------------------------
colnames(wunder.df)
colnames(logger.df)
mrg<-merge(wunder.df,logger.df,"time15") # use common column
colnames(mrg)
head(mrg)

# EXPORT TO CSV -----------------------------------------------------------
getwd()
setwd("C://Users//rapeek//Dropbox//R//wunderground//output")
write.csv(mrg, file=(paste(site, ".csv",sep="")), row.names=FALSE)
write.csv(wunder.df,file=(paste(station, ".csv",sep="")), row.names=FALSE)

# EXPLORATORY PLOTS -------------------------------------------------------

with(mrg, plot(time15,RH,typ="l",lty=1,col="red"))

ylim1=range(mrg$WTemp_C)
ylim2=range(mrg$ATemp_C)
with(mrg, plot(time15,ATemp_C,typ="l",lty=1,col="light gray", ylab=""))
par(new = TRUE)
with(mrg, plot(time15,WTemp_C,typ="l",ylim=range(c(ylim1, ylim2)),lty=1,col="blue", ylab="Temp_C"))
points(loess.smooth(mrg$time15,mrg$WTemp_C),type="l",lty=2, col="dark blue")
points(loess.smooth(mrg$time15,mrg$ATemp_C),type="l",lty=2, col="dark grey")
legend("topleft", inset=.05, title="Temperature (C)",
       c("Air","Water"), col=c("light gray","blue"), lty=c(1,2), lwd=c(1.5,1.5), horiz=FALSE, cex=0.8)

