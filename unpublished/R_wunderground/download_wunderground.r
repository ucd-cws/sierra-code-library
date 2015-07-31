## DOWNLOAD WUNDERGROUND DATA (from Dylan, http://casoilresource.lawr.ucdavis.edu/drupal/node/991)
# be sure to load the function 'wunder_station_daily' first

library(plyr)

# get a single day's worth of (hourly) data
#w <- wunder_station_daily('KCAGROVE6', as.Date('2011-12-05'))

## Setwd based on system name:
if(Sys.info()[4]=="RYAN-PC") {setwd("C://Users//Ryan//Desktop//Dropbox//R//wunderground//download")} else
	{setwd("P://Public//R_Wunderground/download")} # or "C://Users//rapeek//Dropbox//R//wunderground"

# DEFINE STATION ----------------------------------------------------------

#   TUO: KCAGROVE6, MTS026, MD2740
#   AMR: 

station<-'KCAGROVE6' # input station name here

# GET DATA FOR RANGE OF DATES ---------------------------------------------

start<-'2012-01-01'
end<-'2012-07-30'
date.range <- seq.Date(from=as.Date(start), to=as.Date(end), by='1 day')

l <- vector(mode='list', length=length(date.range)) ## pre-allocate list

# LOOP LIST AND FETCH DATA ------------------------------------------------

for(i in seq_along(date.range))
  {
  print(date.range[i])
  l[[i]] <- wunder_station_daily(station, date.range[i])
  }

## stack elements of list into DF, filling missing columns with NA
d <- ldply(l)

# SAVE TO ZIPPED CSV ------------------------------------------------------
getwd()
write.csv(d, file=gzfile(paste(station,".csv.gz", sep="")), row.names=FALSE)

gz<-list.files(pattern=".gz")
#x<-read.csv(file=gzfile(gz),header=TRUE,as.is=TRUE)

rm(list = ls())

# WUNDER STATION DAILY FUNCTION -------------------------------------------

wunder_station_daily <- function(station, date)
  {
  base_url <- 'http://www.wunderground.com/weatherstation/WXDailyHistory.asp?'
  
  # parse date
  m <- as.integer(format(date, '%m'))
  d <- as.integer(format(date, '%d'))
  y <- format(date, '%Y')
  
  # compose final url
  final_url <- paste(base_url,
  'ID=', station,
  '&month=', m,
  '&day=', d, 
  '&year=', y,
  '&format=1', sep='')
  
  # reading in as raw lines from the web server
  # contains <br> tags on every other line
  u <- url(final_url)
  the_data <- readLines(u)
  close(u)
  
  # only keep records with more than 5 rows of data
  if(length(the_data) > 5 )
        {
        # remove the first and last lines
        the_data <- the_data[-c(1, length(the_data))]
        
        # remove odd numbers starting from 3 --> end
        the_data <- the_data[-seq(3, length(the_data), by=2)]
        
        # extract header and cleanup
        the_header <- the_data[1]
        the_header <- make.names(strsplit(the_header, ',')[[1]])
        
        # convert to CSV, without header
        tC <- textConnection(paste(the_data, collapse='\n'))
        the_data <- read.csv(tC, as.is=TRUE, row.names=NULL, header=FALSE, skip=1)
        close(tC)
        
        # remove the last column, created by trailing comma
        the_data <- the_data[, -ncol(the_data)]
        
        # assign column names
        names(the_data) <- the_header
        
        # convert Time column into properly encoded date time
        the_data$Time <- as.POSIXct(strptime(the_data$Time, format='%Y-%m-%d %H:%M:%S'))
        
        # remove UTC and software type columns
        the_data$DateUTC.br. <- NULL
        the_data$SoftwareType <- NULL
        
        # sort and fix rownames
        the_data <- the_data[order(the_data$Time), ]
        row.names(the_data) <- 1:nrow(the_data)
        
        # done
        return(the_data)
        }
  }
  