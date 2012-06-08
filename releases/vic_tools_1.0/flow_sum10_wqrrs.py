# ---------------------------------------------------------------------------
#
# Summary : This script takes daily VIC climate data and converts it to weekly data for use as climate inputs to WQRRS reservoir temperature model
#
# Author  : Scott Ligare
# Created : Feb 5, 2011
#
# Notes   :
# Changes :
#
#===============================================
#Import Modules

import zipfile, csv, os, sys, math
import numpy as np
from time import *

#VIC climate senario
atm = "A2"
scenario = "NCARPCM1"

#______________________________________________________________________________
# reservoir cells is a csv file that lists the VIC files per WQRRS reservoir
p = csv.reader(open('reservoir_cells_2.csv', 'rb'))
resname = []
wat = []
locate = []
fn = []
elev = []
press = []
reslist = []


#set up lists of VIC cells, elvations and subwatershed flux files per reservoir

for row in (p):
    resname.append(row[0])
    wat.append(row[1])
    locate.append(row[2])
    fn.append(row[3])
    elev.append(float(row[4]))
    press.append(float(row[7]))

print "reservoir cells imported"

#reservoir loop

for i in range(9):

    outputfolder = "E:\\Hydra\\VIC\\VWQRRS_Data\\"
    csvwriterwqrrs = csv.writer(open(outputfolder+"WQRRS_input"+resname[i]+"_"+scenario+".csv", "wb"))
##    csvwriterwqrrs_day = csv.writer(open(outputfolder+"WQRRS_input"+resname[i]+"_day.csv", "wb"))

    print "processing reservoir: "+resname[i]
    #csvwriterwqrrs_debug.writerow(("processing reservoir",resname[i]))

    year = []
    dates = []
    wklydates = []
    winds = []
    drybulbs = []
    wetbulbs = []
    relhums = []
    precips = []
    radiations = []

    wklywind = []
    wklydrybulb = []
    wklywetbulb = []
    wklyrelhum = []
    wklyprecip = []
    wklyradiation = []
    wklyyr = []
    startwk = []
    endwk = []

    csvreader = csv.reader(open('E:\\Hydra\\VIC\\SRES'+atm+'\\'+scenario+'\\fluxes\\'+fn[i], "rb"),delimiter='\t')
    for j,row in enumerate(csvreader):
        if j==0:   # set up container to store data.  Note it only does this once per subwatershed
            dates.append(row[0:3])
            winds.append([0.])
            drybulbs.append([0.])
            wetbulbs.append([0.])
            relhums.append([0.])
            precips.append([0.])
            radiations.append([0.])
            winds[j] = 0.
            drybulbs[j] = 0.
            wetbulbs[j] = 0.
            relhums[j] = 0.
            precips[j] = 0.
            radiations[j] = 0.

        wind = (float(row[14]))
        drybulb = (float(row[7]))
        relhum = (float(row[12]))
        precip = (float(row[3]))
        radiation = (float(row[11]))
##        csvwriterwqrrs_debug.writerow(("wind","drybulb","relhum","precip","radiation","press"))
##        csvwriterwqrrs_debug.writerow((wind,drybulb,relhum,precip,radiation,press[i]))

        #calculate wet bulb temp--This formulation is from Snyder and Snow (1984)
        # ESair = Saturation vapor pressure of air temp
        if drybulb >= 0.:
            ESair = 6.108*math.exp((17.27*drybulb)/(drybulb+237.3))
        else:
            ESair = 6.108*math.exp((21.875*drybulb)/(drybulb+265.5))
        # Evp = Saturation vapor pressure
        Evp = (relhum*ESair)/100
        B = (math.log(Evp/6.108))/17.27
        # DP = Dew Point ?
        DP = (237.3*B)/(1-B)

        #initial guess at wetbulb temp
        wetbulb = drybulb
        Ew = 200
        while (abs(Evp-Ew)>0.1):

            if wetbulb >= 0.:
                Esw = 6.108*math.exp((17.27*wetbulb)/(wetbulb+237.3))
            else:
                Esw = 6.108*math.exp((21.875*wetbulb)/(wetbulb+265.5))
            Ew = Esw-.00066*(1+.00115*wetbulb)*(drybulb-wetbulb)*press[i]
            wetbulb = wetbulb - .01
            #print wetbulb

        #Unit conversions - WQRRS uses the imperial metric system
        drybulb = drybulb*9/5+32
        wetbulb = wetbulb*9/5+32
        wind = wind*2.23693629


        winds.append(wind)
        drybulbs.append(drybulb)
        wetbulbs.append(wetbulb)
        relhums.append(relhum)
        precips.append(precip)
        radiations.append(precip)
        #csvwriterwqrrs_debug.writerow((drybulbs[i],wetbulbs[i]))

    #convert daily values to weekly values
    wkcnt = -1
    lycnt = 0
    for y in range(150):
        cy = y+1950
        leapday = 0
        if cy % 4 == 0:
            leapday = 1
        if (cy-1) % 4 == 0:
            lycnt += 1
        for w in range(52):
            wkcnt = wkcnt + 1
            startwk.append((y-lycnt)*365+lycnt*366+w*7)
            daysinweek = 7
            if w==51: daysinweek += 1 + leapday
            endwk.append(startwk[wkcnt] + daysinweek)

            wklywind.append(sum(winds[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklydrybulb.append(sum(drybulbs[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklywetbulb.append(sum(wetbulbs[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyrelhum.append(sum(relhums[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyprecip.append(sum(precips[startwk[wkcnt]:endwk[wkcnt]]))
            wklyradiation.append(sum(radiations[startwk[wkcnt]:endwk[wkcnt]]))

            wklydates.append(w+1)
            wklyyr.append(cy)


    # dates: 3679,4667=wk40,2020-wk39-2040

    csvwriterwqrrs.writerow((("Date(yymmdd)","Date (yymmddhh)","","Sky Cover Fraction (0-1)","Dry Bulb (F)","Wet Bulb (F)","Atmo Press (Hg)","Wind Speed (mph")))
    #for j in range(3679,4667):
    for j in range(7799):
        csvwriterwqrrs.writerow(("","","Wk "+str(wklydates[j])+" "+str(wklyyr[j]),"1",wklydrybulb[j],wklywetbulb[j],press[i],wklywind[j]))

    #csvwriterwqrrs_day.writerow((("Date(yymmdd)","Date (yymmddhh)","","Sky Cover Fraction (0-1)","Dry Bulb (F)","Wet Bulb (F)","Atmo Press (inHg)","Wind Speed (mph")))
    #for j in range(46):
     #   csvwriterwqrrs_day.writerow(("","","Wk "+str(dates[j])+" "+str(year[j]),"1",drybulbs[j],wetbulbs[j],press[i],winds[j]))


