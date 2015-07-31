##AGGREGATE TEMP DATA
## PEEK 03-Oct-2012


# GET WUNDER ADJUSTED FILE ------------------------------------------------

inputfile <- choose.files(getwd())
inputfile <- "C://Users//Ryan//Desktop//Dropbox//R//wunderground//output//Clavey_solinst_Wundr_mrg_2012.csv"
inputfile <- "C://Users//rapeek//Dropbox//R//wunderground//output//Clavey_solinst_Wundr_mrg_2012.csv"
wunder<-read.csv(inputfile,stringsAsFactors=FALSE)
dim(wunder) #lists total columns of dataset
head(wunder)
df<-data.frame(wunder) # Create dataframe
summary(df)
# DATETIME CONVERSIONS-----------------------------------------------------

df$time15lt<-strptime(df$time15,format="%Y-%m-%d %H:%M:%S") # convert to datetime
str(unclass(df$time15lt)) # view POSIXlt classes to reaggregate by
#df$year<-df$time15$year+1900
#df$yday<-df$time15$yday
#df$timefrac<-(df$time15$hour) + (df$time15$min/60)
df$day<-trunc(df$time15lt, "day")
df$hour<-trunc(df$time15lt, "hour")

head(df)
str(df)
names(df)

# USE LUBRIDATE (this method is slower) -----------------------------------
#require(lubridate)
#df$time15<-ymd_hms(df$time15) # creates POSIXct datetime
#df$time15lt<-as.POSIXlt(df$time15) # converts to POSIXlt datetime (to use classes)

# REAGGREGATE 15 MIN DATA to DAILY ----------------------------------------

require(plyr)
df.daily<-ddply(df,.(day),summarize,
                meanWTemp=mean(WTemp_C), 
                meanATemp=mean(ATemp_C),
                meanStage=mean(stage_m),
                mean_dyrain_in=mean(dailyrainin),
                mean_Humid=mean(Humidity),
                meanBaroHg_in=mean(PressureIn))


head(df.daily)
summary(df.daily)
df.daily$mon<-df.daily$day$mon
## quick plots to check data
plot(df.daily$day, df.daily$Hrsum_dyrain_in,type="l")
plot(df.daily$day, df.daily$mean_Humid,type="l")

## export to CSV
getwd()
write.csv(df.daily, file=("Clavey_solinst_Wundr_dy_2012.csv"), row.names=FALSE)

# REAGGREGATE 15 MIN DATA to HOURLY ---------------------------

require(plyr)
df.hourly<-ddply(df,.(hour),summarize,
                 meanWTemp=mean(WTemp_C), 
                 meanATemp=mean(ATemp_C),
                 meanStage=mean(stage_m),
                 Hrsum_dyrain_in=sum(dailyrainin),
                 mean_Humid=mean(Humidity),
                 meanBaroHg_in=mean(PressureIn))
  
head(df.hourly)
summary(df.hourly)
## quick plots to check data
plot(df.hourly$hour, df.hourly$Hrsum_dyrain_in,type="l", col="red")
plot(df.hourly$hour, df.hourly$mean_Humid,type="l")

## export to CSV
write.csv(df.hourly, file=("Clavey_solinst_Wundr_hr_2012.csv"), row.names=FALSE)

# PLOTTING ----------------------------------------------------------------

## HOURLY 
ylim1=range(df.hourly$meanWTemp)
ylim2=range(df.hourly$meanATemp)
with(df.hourly, plot(hour,meanATemp,typ="l",lty=1,col="light gray", ylab=""))
par(new = TRUE)
with(df.hourly, plot(hour,meanWTemp,typ="l",ylim=range(c(ylim1, ylim2)),lty=1,col="blue", ylab="Temp_C"))
legend("topleft", inset=.05, title="Temperature (C)",
       c("Air","Water"), col=c("light gray","blue"), lty=c(1,2), lwd=c(1.5,1.5), horiz=FALSE, cex=0.8)


## DAILY
ylim1=range(df.daily$meanWTemp)
ylim2=range(df.daily$meanATemp)
with(df.daily, plot(day,meanATemp,typ="l",lty=1,col="light gray", ylab="", xlab=""))
par(new = TRUE)
with(df.daily, plot(day,meanWTemp,typ="l",ylim=range(c(ylim1, ylim2)),lty=1,col="blue", ylab="Temp_C", xlab=""))
legend("topleft", inset=.05, title="Temperature (C)",
       c("Air","Water"), col=c("light gray","blue"), lty=c(1,2), lwd=c(1.5,1.5), horiz=FALSE, cex=0.8)


# ggplot using color gradient with variable--------------------------------

require(ggplot2)

## HOURLY wTemp vs airTemp
hourly <- ggplot(df.hourly, aes(x=hour, y=meanWTemp)) +
  geom_line(aes(colour=meanStage))+
  scale_colour_gradient(low="light blue 3",high="red")
hr<-hourly +scale_y_continuous(breaks=seq(0,32,4)) +
  labs(title="TEST\n FOR Clavey") + ylab("Water Temp (C)") + 
  xlab("") + geom_hline(aes(yintercept=12), size=.7, colour="#E69F00", linetype="dashed")
hr

## HOURLY meanStage vs daily rain sum
hourly <- ggplot(df.hourly, aes(x=hour, y=meanStage)) +
  geom_line(aes(colour=Hrsum_dyrain_in))+
  scale_colour_gradient(low="light blue 3",high="red")
hr<-hourly + labs(title="TEST\n FOR Clavey") + ylab("Stage (m)") + xlab("")
hr

## DAILY
daily <- ggplot(df.daily, aes(x=day, y=meanWTemp)) + 
  geom_line(aes(colour=meanStage),linetype = 1, size=1.1) +
  scale_colour_gradient(low="light blue",high="red")
dy<-daily + scale_y_continuous(breaks=seq(0,28,4)) + 
  labs(title="TEST\n FOR Clavey") + 
  ylab("Water Temp (C)") + xlab("")
dy

## DAILY meanStage vs daily rain sum
daily <- ggplot(df.daily, aes(x=day, y=meanStage)) +
  geom_line(aes(colour=mean_dyrain_in))+
  scale_colour_gradient(low="light blue 3",high="red")
dy<-daily + labs(title="TEST\n FOR Clavey") + ylab("Stage (m)") + xlab("")
dy

## COPY figures to folder
#setwd("P://Private//R//results//Spring_Recsn")
#dev.copy(png,"clavey_multicol.png", width=400, height=400)
#ggsave("clavey_multicol.png.pdf", width=5, height=4, dpi=72)
#dev.off()