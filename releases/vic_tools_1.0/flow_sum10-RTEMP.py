# ---------------------------------------------------------------------------
#
# Summary : This script takes daily VIC climate data and converts it to weekly climate data for use as inflows to WEAP and RTEMP
#
# Author  : Scott Ligare
# Created : Jan 29, 2011
#
# Notes   :
#
# Changes :
#
#===============================================
#Import Modules

import zipfile, csv, os, sys
import numpy as np
from time import *

#VIC climate senario
atm = "A2"
scenario = "NCARPCM1"
#scenario = "MIROC32MED"
timeperiod = "ftp"
location = "southern"
#______________________________________________________________________________
# cell_area_lookup is a csv file that lists the VIC files per WEAP subwatershed and provides the contrubuting areas in m2
p = csv.reader(open('good_file_areas5_STN_northerncells.csv', 'rb'))
areadict={}
fndict={}

#set up dictionarys of VIC cell areas and subwatershed flux files
try:
    for row in (p):
        subwat = row[0]
        fname = row[1]
        cell = row[2]
        area = float(row[3])
        areadict[cell]=(area)
        if fndict.keys().count(subwat)==0:
            fndict[subwat]=[]
        fndict[subwat].append(fname)
    #print areadict
    print "lookup areas imported into dictionary"
except:
    print "error creating dictionary of cell areas"

subwatlist = []

#set up file arrays (really just nested lists)

runoffarray = []
windarray =[]
airtemparray =[]
relhumarray = []
preciparray = []
snowmeltarray = []
snowaccuarray = []
basearray = []
radarray = []
interarray = []

#_____________________________________________________________________________
#subwatershed loop
for numsubwat,subwat in enumerate(fndict.keys()):
##    csvwriter = csv.writer(open('E:\\Home\\stligare\\Public\\pythoncodeetc_\\Output\\'+subwat+"_out.csv", "wb"))
##    csvwriterwkly = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'_'+scenario+'\\'+subwat+"_Flow_to_River.csv", "wb"))
##    csvwriterweap = csv.writer(open('E:\\Home\\stligare\\Public\\pythoncodeetc_\\Output\\WEAP\\'+subwat+"_Flow_to_River.csv", "wb"))

    csvwriterrtempbase = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_Baseflow_"+atm+scenario+".csv", "wb"))
    csvwriterrtempflow = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_SurfaceRunoff_"+atm+scenario+".csv", "wb"))
    csvwriterrtempwind = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_WindSpeed_"+atm+scenario+".csv", "wb"))
    csvwriterrtempairtemp = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_Temperature_"+atm+scenario+".csv", "wb"))
    csvwriterrtemprelhum = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_Humidity_"+atm+scenario+".csv", "wb"))
##    csvwriterrtempsnow = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'\\'+subwat+"_snow.csv", "wb"))
    csvwriterrtempprecip = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_Precipitation_"+atm+scenario+".csv", "wb"))
    csvwriterrtempsnowmeltvol = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_SnowMelt_"+atm+scenario+".csv", "wb"))
    csvwriterrtempsnowaccu = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_SnowAccumulation_"+atm+scenario+".csv", "wb"))
##    csvwriterrtempinterflow = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'_'+scenario+"\\"+timeperiod+"_Interflow_"+atm+scenario+".csv", "wb"))
    csvwriterrtempradiation = csv.writer(open('E:\\Hydra\\VIC\\VRTEMP_DATA\\'+location+'\\'+timeperiod+"_SolarRadiation_"+atm+scenario+".csv", "wb"))

##    csvwriterrtempdailytest = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'_'+scenario+"_dailytest.csv", "wb"))
##    csvwriterrtempdailytestsnow = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'_'+scenario+"_dailytestsnow.csv", "wb"))

    print "processing subwatershed: "+subwat
    dates = []
    wklydates = []
    flows = []
    bases = []
    winds = []
    airtemps = []
    relhums = []
    precips = []
    deltasnow = []
    snowmeltvols = []
    snowaccus = []
    snows = []
    interflows = []
    radiations = []
    flowstoriver = []
    wklyflows = []
    wklybases = []
    wklyflowstoriver = []
    wklywind = []
    wklyairtemp = []
    wklyrelhum = []
    wklyprecip = []
    wklysnowmeltvol = []
    wklysnow = []
    wklysnowaccu = []
    wklyinterflow = []
    wklyradiation = []
    wklyyr = []
    startwk = []
    endwk = []

    subwatarea = 0.
    #calculate total subwat area
    for file,filenum in enumerate(fndict[subwat]):
        subflux = subwat+filenum
        subwatarea = subwatarea + areadict[subflux]
    #print "subwatarea = ",subwatarea


    #file loop
    for f,fn in enumerate(fndict[subwat]):
        print "processing VIC file: "+fn
        csvreader = csv.reader(open('E:\\Hydra\\VIC\\SRES'+atm+'\\'+scenario+'\\fluxes\\'+fn, "rb"),delimiter='\t')
        #csvreader = csv.reader(open('E:\\Hydra\\VIC\\SRESA2\\'+scenario+'\\fluxes\\'+fn, "rb"),delimiter='\t')
        #csvreader = csv.reader(open('E:\\Hydra\\VIC\\VIC_Streamflow\\VIC_hist_fluxes\\'+fn+'.csv', "rb"),delimiter=',')
        #csvreader = csv.reader(open('E:\\Hydra\\VIC\\SRESA2\\CNRMCM3\\fluxes\\fluxes_test.1875', "rb"),delimiter='\t')
        #try:
        for i,row in enumerate(csvreader):
            if f==0:   # set up container to store data.  Note it only does this once per subwatershed
                dates.append(row[0:3])
                flows.append([0.])
                bases.append([0.])
                flowstoriver.append([0.])
                winds.append([0.])
                airtemps.append([0.])
                relhums.append([0.])
                precips.append([0.])
                snowmeltvols.append([0.])
                snowaccus.append([0.])
                snows.append([0.])
                interflows.append([0.])
                radiations.append([0.])
                flows[i] = 0.
                bases[i] = 0.
                winds[i] = 0.
                airtemps[i] = 0.
                relhums[i] = 0.
                precips[i] = 0.
                snows[i] = 0.
                snowmeltvols[i] = 0.
                snowaccus[i] = 0.
                interflows[i] = 0.
                radiations[i] = 0.
                flowstoriver[i] = 0.


            #read in flow values and convert to volumetric runoff by multiplying by area of cell and other climate data
            subflux = subwat+fn
            #print subflux
            #print areadict[subflux]
            #print row
            #print row(5)
            flow = (float(row[5]))*.001*areadict[subflux]
            base = (float(row[6]))*.001*areadict[subflux]
            flowtoriver = flow + base
            wind = (float(row[14]))*(areadict[subflux]/subwatarea)
            airtemp = (float(row[7]))*(areadict[subflux]/subwatarea)
            relhum = (float(row[12]))*(areadict[subflux]/subwatarea)
            precip = (float(row[3]))*.001*areadict[subflux]
            snow = (float(row[13]))*.001*areadict[subflux]
            interflow = ((float(row[8]))+(float(row[9]))+(float(row[10])))*.001*areadict[subflux]
            radiation = (float(row[11]))*(areadict[subflux]/subwatarea)


            # add flows from VIC points to flows list
            flows[i] = flows[i] + flow
            bases[i] = bases[i] + base
            flowstoriver[i] = flowstoriver[i] + flowtoriver
            winds[i] = winds[i] + wind
            airtemps[i] = airtemps[i] + airtemp
            relhums[i] = relhums[i] + relhum
            precips[i] = precips[i] + precip
            snows[i] = snows[i] + snow
            interflows[i] = interflows[i] + interflow
            radiations[i] = radiations[i] + radiation


    #except:
        #print "error with flows"
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

            wklyflows.append(sum(flows[startwk[wkcnt]:endwk[wkcnt]]))


            wklybases.append(sum(bases[startwk[wkcnt]:endwk[wkcnt]]))
            wklyflowstoriver.append(sum(flowstoriver[startwk[wkcnt]:endwk[wkcnt]]))
            wklywind.append(sum(winds[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyairtemp.append(sum(airtemps[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyrelhum.append(sum(relhums[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyprecip.append(sum(precips[startwk[wkcnt]:endwk[wkcnt]]))
            wklysnow.append(sum(snows[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)
            wklyinterflow.append(sum(interflows[startwk[wkcnt]:endwk[wkcnt]]))
            wklyradiation.append(sum(radiations[startwk[wkcnt]:endwk[wkcnt]]))

            wklydates.append(w+1)
            wklyyr.append(cy)
            #print wklyflowstoriver

            # calculating the snowmelt v. snowaccumulation values.  If there is more snow at current than last timestep then snowaccu is positive, if less then snow melt is positive
            if wkcnt == 0 :
                wklysnowmeltvol.append(0.)
                wklysnowaccu.append(0.)
            else :
                if wklysnow[wkcnt] > wklysnow[wkcnt-1]:
                    wklysnowmeltvol.append(0.)
                    wklysnowaccu.append(wklysnow[wkcnt]-wklysnow[wkcnt-1])
                elif wklysnow[wkcnt] < wklysnow[wkcnt-1]:
                    wklysnowmeltvol.append(wklysnow[wkcnt-1]-wklysnow[wkcnt])
                    wklysnowaccu.append(0.)
                else:
                    wklysnowmeltvol.append(0.)
                    wklysnowaccu.append(0.)

    subwatlist.append(subwat)

    #write subwat info to array
    runoffarray.append(wklyflows)
    windarray.append(wklywind)
    airtemparray.append(wklyairtemp)
    relhumarray.append(wklyrelhum)
    preciparray.append(wklyprecip)
    snowmeltarray.append(wklysnowmeltvol)
    snowaccuarray.append(wklysnowaccu)
    basearray.append(wklybases)
    radarray.append(wklyradiation)
    interarray.append(wklyinterflow)


#time periods: hist period 1961-1990 (cal)= 559,2171
#              near term period 2005-2034 = 2847,4459
#              mid term period  2035-2064 = 4407 - 6019
#              far term period  2070-2099 = 6227 - 7787 (note this period ends at water year 2099)
if timeperiod == "htp":
    periodst=559
    periodend=2171
elif timeperiod == "ntp":
    periodst=2847
    periodend=4459
elif timeperiod == "mtp":
    periodst=4407
    periodend=6019
elif timeperiod == "ftp":
    periodst=6227
    periodend=7787

#csvwriterrtempflow.writerow(("Wk ","STN_01","STN_02","STN_03","STN_04","STN_05","STN_06","STN_07","STN_07","STN_08","STN_09","STN_10","STN_11","STN_12","STN_13","STN_14","STN_15","STN_16","STN_17","STN_18","STN_19","STN_20","STN_21","STN_22","STN_23","STN_24","STN_25"))
csvwriterrtempflow.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempflow.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),runoffarray[0][j],runoffarray[1][j],runoffarray[2][j],runoffarray[3][j],runoffarray[4][j],runoffarray[5][j],runoffarray[6][j],runoffarray[7][j],runoffarray[8][j],runoffarray[9][j],runoffarray[10][j],runoffarray[11][j],runoffarray[12][j],runoffarray[13][j],runoffarray[14][j],runoffarray[15][j],runoffarray[16][j],runoffarray[17][j],runoffarray[18][j],runoffarray[19][j],runoffarray[20][j],runoffarray[21][j],runoffarray[22][j],runoffarray[23][j],runoffarray[24][j]))

csvwriterrtempbase.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempbase.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),basearray[0][j],basearray[1][j],basearray[2][j],basearray[3][j],basearray[4][j],basearray[5][j],basearray[6][j],basearray[7][j],basearray[8][j],basearray[9][j],basearray[10][j],basearray[11][j],basearray[12][j],basearray[13][j],basearray[14][j],basearray[15][j],basearray[16][j],basearray[17][j],basearray[18][j],basearray[19][j],basearray[20][j],basearray[21][j],basearray[22][j],basearray[23][j],basearray[24][j]))

csvwriterrtempwind.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempwind.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),windarray[0][j],windarray[1][j],windarray[2][j],windarray[3][j],windarray[4][j],windarray[5][j],windarray[6][j],windarray[7][j],windarray[8][j],windarray[9][j],windarray[10][j],windarray[11][j],windarray[12][j],windarray[13][j],windarray[14][j],windarray[15][j],windarray[16][j],windarray[17][j],windarray[18][j],windarray[19][j],windarray[20][j],windarray[21][j],windarray[22][j],windarray[23][j],windarray[24][j]))

csvwriterrtempairtemp.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempairtemp.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),airtemparray[0][j],airtemparray[1][j],airtemparray[2][j],airtemparray[3][j],airtemparray[4][j],airtemparray[5][j],airtemparray[6][j],airtemparray[7][j],airtemparray[8][j],airtemparray[9][j],airtemparray[10][j],airtemparray[11][j],airtemparray[12][j],airtemparray[13][j],airtemparray[14][j],airtemparray[15][j],airtemparray[16][j],airtemparray[17][j],airtemparray[18][j],airtemparray[19][j],airtemparray[20][j],airtemparray[21][j],airtemparray[22][j],airtemparray[23][j],airtemparray[24][j]))

csvwriterrtemprelhum.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtemprelhum.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),relhumarray[0][j],relhumarray[1][j],relhumarray[2][j],relhumarray[3][j],relhumarray[4][j],relhumarray[5][j],relhumarray[6][j],relhumarray[7][j],relhumarray[8][j],relhumarray[9][j],relhumarray[10][j],relhumarray[11][j],relhumarray[12][j],relhumarray[13][j],relhumarray[14][j],relhumarray[15][j],relhumarray[16][j],relhumarray[17][j],relhumarray[18][j],relhumarray[19][j],relhumarray[20][j],relhumarray[21][j],relhumarray[22][j],relhumarray[23][j],relhumarray[24][j]))

csvwriterrtempprecip.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempprecip.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),preciparray[0][j],preciparray[1][j],preciparray[2][j],preciparray[3][j],preciparray[4][j],preciparray[5][j],preciparray[6][j],preciparray[7][j],preciparray[8][j],preciparray[9][j],preciparray[10][j],preciparray[11][j],preciparray[12][j],preciparray[13][j],preciparray[14][j],preciparray[15][j],preciparray[16][j],preciparray[17][j],preciparray[18][j],preciparray[19][j],preciparray[20][j],preciparray[21][j],preciparray[22][j],preciparray[23][j],preciparray[24][j]))

csvwriterrtempsnowmeltvol.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempsnowmeltvol.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),snowmeltarray[0][j],snowmeltarray[1][j],snowmeltarray[2][j],snowmeltarray[3][j],snowmeltarray[4][j],snowmeltarray[5][j],snowmeltarray[6][j],snowmeltarray[7][j],snowmeltarray[8][j],snowmeltarray[9][j],snowmeltarray[10][j],snowmeltarray[11][j],snowmeltarray[12][j],snowmeltarray[13][j],snowmeltarray[14][j],snowmeltarray[15][j],snowmeltarray[16][j],snowmeltarray[17][j],snowmeltarray[18][j],snowmeltarray[19][j],snowmeltarray[20][j],snowmeltarray[21][j],snowmeltarray[22][j],snowmeltarray[23][j],snowmeltarray[24][j]))

csvwriterrtempsnowaccu.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempsnowaccu.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),snowaccuarray[0][j],snowaccuarray[1][j],snowaccuarray[2][j],snowaccuarray[3][j],snowaccuarray[4][j],snowaccuarray[5][j],snowaccuarray[6][j],snowaccuarray[7][j],snowaccuarray[8][j],snowaccuarray[9][j],snowaccuarray[10][j],snowaccuarray[11][j],snowaccuarray[12][j],snowaccuarray[13][j],snowaccuarray[14][j],snowaccuarray[15][j],snowaccuarray[16][j],snowaccuarray[17][j],snowaccuarray[18][j],snowaccuarray[19][j],snowaccuarray[20][j],snowaccuarray[21][j],snowaccuarray[22][j],snowaccuarray[23][j],snowaccuarray[24][j]))

csvwriterrtempradiation.writerow(("Wk ",subwatlist[0],subwatlist[1],subwatlist[2],subwatlist[3],subwatlist[4],subwatlist[5],subwatlist[6],subwatlist[7],subwatlist[8],subwatlist[9],subwatlist[10],subwatlist[11],subwatlist[12],subwatlist[13],subwatlist[14],subwatlist[15],subwatlist[16],subwatlist[17],subwatlist[18],subwatlist[19],subwatlist[20],subwatlist[21],subwatlist[22],subwatlist[23],subwatlist[24]))
for j in range(periodst,periodend):
    csvwriterrtempradiation.writerow(("Wk "+str(wklydates[j])+" "+str(wklyyr[j]),radarray[0][j],radarray[1][j],radarray[2][j],radarray[3][j],radarray[4][j],radarray[5][j],radarray[6][j],radarray[7][j],radarray[8][j],radarray[9][j],radarray[10][j],radarray[11][j],radarray[12][j],radarray[13][j],radarray[14][j],radarray[15][j],radarray[16][j],radarray[17][j],radarray[18][j],radarray[19][j],radarray[20][j],radarray[21][j],radarray[22][j],radarray[23][j],radarray[24][j]))




