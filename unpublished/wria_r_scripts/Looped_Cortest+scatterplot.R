##Kern and Pixley Groundwater Level Data Analysis##
##Perform Kendall correlation test and output graph with lowess line##
##cortest+scatterplot.R##
##Created by Eric Holmes##

library(foreign)
library(zyp)
#library(plotrix)

setwd("C:/Users/Eric/Documents/USFWS/GroundwaterDataAnalysis/WellData/JulianDatescsv/Non-growing")

tables <- list.files(pattern=".csv")  #list csvs 

for (table in tables) {

alldata<-read.csv(table, header=TRUE)  #read csv
#ls(alldata) #quickly makes sure data was read in appropriately
alldatas1<-subset(alldata, alldata$jdate>1970 & alldata$jdate<2004)  #store a subset of the full data set

filename<-substr(basename(table),1,13) #this stores a trimmed filename string to be used in the pdf file naem and the plot title below

x <- alldatas1$date
y <- alldatas1$WSE
j <- alldatas1$jdate
w <- as.Date(x,"%m/%d/%Y")
#v <- strptime(as.character(alldata$date), "%m/%d/%Y")

t1<- cor.test(j,y,alternative=c("two.sided"),method=c("kendall"),exact=NULL, conf.level = .95, continuity=FALSE)$estimate
t<-signif(t1,6)
p1<-cor.test(j,y,alternative=c("two.sided"),method=c("kendall"),exact=NULL, conf.level = .95, continuity=FALSE)$p.value
p<-signif(p1,6)
zyp.sen(y~j)
s1<-zyp.sen(y~j)$coefficient
s<-signif(s1,6)

pdf(paste("1970-2004_Plot_",filename,"ng",".pdf", sep=""))
plot(w, y, ylab="Water Surface Elevation", xlab="Year", main=paste("Well ", filename,"\n","Non-Growing Season" ,sep=""))
spanlist <- c(.5,1,2)
points(loess.smooth(w,y), span=.5, lwd=3, col=2)
#for (i in 1:length(spanlist)) {
  #lines(loess.smooth(w, y),span=spanlist[i], lwd=3, col=i)}
#lines(loess.smooth(w, y),span=2, lwd=3, col=1)
#lines(loess.smooth(w, y),span=.5, lwd=3, col=3)
mtext(paste("p value=",p,sep=""),side=1,line=-1, col=2, cex=1)
mtext(paste("tau=",t,sep=""),side=1, line=-2, col=1, cex=1)
mtext(s,side=1, line=-3, col=3, cex=1)
}