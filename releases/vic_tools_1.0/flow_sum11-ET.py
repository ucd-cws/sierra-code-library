# ---------------------------------------------------------------------------
#
# Summary : This script calculates annual ET values per subwat from VIC climate data
#
# Author  : Scott Ligare
# Created : Feb 14, 2011
#
# Notes   :
#
# Changes :
#
#===============================================
#Import Modules

import zipfile, csv, os, sys
from time import *

#atmlist = ["A2","B1"]
atmlist = ["A2"]
#scenariolist = ["CNRMCM3","GFDLCM21","MIROC32MED","MPIECHAM5","NCARPCM1"]
scenariolist = ["NCARCCSM3"]
#______________________________________________________________________________
# cell_area_lookup is a csv file that lists the VIC files per WEAP subwatershed and provides the contrubuting areas in m2
p = csv.reader(open('good_file_areas5.csv', 'rb'))
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

watlist = ["AMR","BAR","CAL","COS","FEA","KAW","KNG","KRN","LYB","MER","MOK","SJN","STN","TUL","TUO","YUB"]
subwatlist = []

#set up file arrays (really just nested lists)
etarray = []

csvwriterweapet = csv.writer(open('E:\\Hydra\\VIC\\VIC_ET_Data\\VIC_ET_3.csv', "wb"))
csvwriterweapet.writerow(("atm","scenario","subwat","year (WY)","ET (m3)"))
#_____________________________________________________________________________
#atm loop
for atmcnt, atm in enumerate(atmlist):

    #_____________________________________________________________________________
    #scenario loop
    for scenariocnt, scenario in enumerate(scenariolist):

        #_____________________________________________________________________________
        #subwatershed loop
        for numsubwat,subwat in enumerate(fndict.keys()):

            print "processing subwatershed: "+subwat, atmlist[atmcnt],scenariolist[scenariocnt]
            dates = []
            wklydates = []
            ets = []
            wklyet = []
            yrlyet = []
            wklyyr = []
            startwk = []
            startyr = []
            endwk = []
            endyr = []
            wateryr = []

            subwatarea = 0.
            #calculate total subwat area
            for file,filenum in enumerate(fndict[subwat]):
                subflux = subwat+filenum
                subwatarea = subwatarea + areadict[subflux]
            #print "subwatarea = ",subwatarea


            #file loop
            for f,fn in enumerate(fndict[subwat]):
                print "processing VIC file: "+fn

                csvreader = csv.reader(open('E:\\Hydra\\VIC\\SRES'+atmlist[atmcnt]+'\\'+scenariolist[scenariocnt]+'\\fluxes_2\\'+fn, "rb"),delimiter='\t')
                #try:
                for i,row in enumerate(csvreader):
                    if f==0:   # set up container to store data.  Note it only does this once per subwatershed
                        dates.append(row[0:3])
                        ets.append([0.])
                        ets[i] = 0.

                    #read in flow values and convert to volumetric runoff by multiplying by area of cell and other climate data
                    subflux = subwat+fn
                    et = (float(row[4]))*(areadict[subflux]/subwatarea)*.001*areadict[subflux]

                    # add flows from VIC points to flows list

                    ets[i] = ets[i] + et

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
                    wklyet.append(sum(ets[startwk[wkcnt]:endwk[wkcnt]]))
                    wklydates.append(w+1)
                    wklyyr.append(cy)

                #convert wkly flows to annual flows (water year)
            yrcnt = -1

            for y in range(150):
                wy = y+1951
                yrcnt = yrcnt + 1
                startyr = (52*yrcnt)+39
                endyr = (52*(yrcnt+1))+39
                yrlyet.append(sum(wklyet[startyr:endyr]))
                wateryr.append(wy)

            subwatlist.append(subwat)

            for j in range(149):
                csvwriterweapet.writerow((atm,scenario,subwat,wateryr[j],yrlyet[j]))


##csvwriterweapet.writerow(("subwat","year","week",atmlist[0]+scenariolist[0],atmlist[0]+scenariolist[1],atmlist[0]+scenariolist[2],atmlist[0]+scenariolist[4],atmlist[0]+senariolist[4],atmlist[0]+scenariolist[5],atmlist[1]+scenariolist[0],atmlist[1]+scenariolist[1],atmlist[1]+scenariolist[2],atmlist[1]+scenariolist[4],atmlist[1]+scenariolist[4],atmlist[1]+scenariolist[5]))
##for j in range(7800):
##    csvwriterweapet.writerow((subwatlist[j],wklyyr[j],wklydates[j],etarray[0][j],etarray[1][j],etarray[2][j],etarray[3][j],etarray[4][j],etarray[5][j],etarray[6][j],etarray[7][j],etarray[8][j],etarray[9][j],etarray[10][j],etarray[11][j]))
#csvwriterweapet.writerow(("atm","scenario","subwat","year (WY)","ET (m3)"))
