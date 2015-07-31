### Making Thermohydrographs using ggplot2
### Ryan Peek 2013

pkgs <- c("lubridate","grid","scales","ggplot2") # list packages

# install packages
pkgs <- pkgs[!(pkgs %in% installed.packages()[,"Package"])]
if(length(pkgs)) install.packages(pkgs,repos="http://cran.cs.wwu.edu/")
library(lubridate)
library(grid)
library(scales)
library(ggplot2)


# GET FILES ---------------------------------------------------------------

site="Clavey"
year=2013
date="_09_20"
## this is the stage/temp data current
inputfile<-file.choose()

## import stage/temp data and format 
dataplot<-read.csv(inputfile,stringsAsFactors=FALSE)
dim(dataplot) #lists total columns of dataset

dataplot$Date<-ymd_hms(dataplot$Datetime) # depending on Date Format
# dataplot$Date<-mdy_hm(dataplot$Date) # or use this 

##### DIFFERENT COLOR TEMPLATES: ----------------------------------------------

## 3 C Steps: Use as Default
breaks<-(c(3,6,9,12,15,18,21,24,27)) # for color scale
palette<-c("midnightblue","blue","deepskyblue2","green4","green","yellow","orange","orangered","brown4")

## 4 C Steps
breaks<-(c(0,4,8,12,16,20,24,28)) 
palette<-c("dark blue","blue","light blue","green","yellow","orange","orangered","brown4")

## 4 C Steps: For Warmer Temps
breaks<-(c(0,4,8,12,16,20,24,28,32,36)) # for color scale
palette<-c("dark blue","blue","light blue","green","yellow","orange","orangered","darkred","maroon","gray40","gray5")


##### TO FILTER OUT DISCONTINUOUS DATA use breaks as groups and add to aes()-------

idx<-c(1,diff(dataplot$Datetime)) # make a diff column
i2<-c(1,which(idx!=1),nrow(dataplot)+1) # compare which rows are are not diff by 15 min
dataplot$grp<-rep(1:length(diff(i2)),diff(i2)) # use group to assign each portion of plotted line

# THERMOHYDROGRAPH --------------------------------------------------------
thermohydro1<-(ggplot() + geom_line(data=dataplot,aes(group=grp,x=Datetime, y=Level, colour=Temperature), size=0.65,alpha=1) +
                 ylab("Stage (m)") + xlab("") +
                 scale_x_datetime(breaks=date_breaks("1 months"),labels = date_format("%b-%y"))+
                 scale_colour_gradientn("Water \nTemp (C)",colours=palette(palette),
                                        values=breaks, rescaler = function(x, ...) x, 
                                        oob = identity,limits=c(0,27), breaks=breaks, 
                                        space="Lab") +theme_bw() + 
                 labs(title="Hourly Thermohydrograph")+
                 theme(axis.text.x = element_text(angle = 45, hjust = 1)))
print(thermohydro1)


