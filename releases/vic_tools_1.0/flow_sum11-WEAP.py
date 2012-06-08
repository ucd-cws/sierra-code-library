# ---------------------------------------------------------------------------
#
# Summary : This script takes daily VIC flow data and converts it to weekly flow data for use as inflows to WEAP and RTEMP
#
# Author  : Scott Ligare
# Created : Jan 12, 2011
#
# Notes   : This was written with help from David Rheinnheimer
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
#scenario = "NCARPCM1"
#______________________________________________________________________________
# cell_area_lookup is a csv file that lists the VIC files per WEAP subwatershed and provides the contrubuting areas in m2
p = csv.reader(open('good_file_areas5_STN_southerncells.csv', 'rb'))
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

#scenariolist = ["CNRMCM3","GFDLCM21","MIROC32MED","MPIECHAM5","NCARCCSM3","NCARPCM1"]
scenariolist = ["MIROC32MED","NCARPCM1"]
#scenariolist = ["NCARCCSM3"]
#atmlist = ["A2","B1"]
atmlist = ["A2"]
watlist = ["STN"]
#watlist = ["AMR","BAR","CAL","COS","FEA","KAW","KNG","KRN","LYB","MER","MOK","SJN","STN","TUL","TUO","YUB"]
subwatlist = []
location = "southern"

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
#scenario loop
for scenariocnt, scenario in enumerate(scenariolist):

    #_____________________________________________________________________________
    #subwatershed loop
    for numsubwat,subwat in enumerate(fndict.keys()):
    ##    csvwriter = csv.writer(open('E:\\Home\\stligare\\Public\\pythoncodeetc_\\Output\\'+subwat+"_out.csv", "wb"))
    ##    csvwriterwkly = csv.writer(open('E:\\Hydra\\VIC\\temp_intermediate_out\\mid_sierra_unimpaired\\'+atm+'_'+scenario+'\\'+subwat+"_Flow_to_River.csv", "wb"))
    ##    csvwriterweap = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Inflows\\'+subwat+"_Flow_to_River.csv", "wb"))
    ##    csvwriterweaprelhum = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Climate\\'+subwat+"_Humidity.csv", "wb"))
    ##    csvwriterweapradiation = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Climate\\'+subwat+"_Net_Solar_Radiation.csv", "wb"))
    ##    csvwriterweapprecip = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Climate\\'+subwat+"_Precipitation.csv", "wb"))
    ##    csvwriterweaptemp = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Climate\\'+subwat+"_Temperature.csv", "wb"))
    ##    csvwriterweapwind = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+scenario+'\\Climate\\'+subwat+"_Wind.csv", "wb"))

        print "processing subwatershed: "+subwat, scenario
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
                flow = (float(row[5]))*.001*areadict[subflux]
                base = (float(row[6]))*.001*areadict[subflux]
                flowtoriver = flow + base
                wind = (float(row[14]))*(areadict[subflux]/subwatarea)
                airtemp = (float(row[7]))*(areadict[subflux]/subwatarea)
                relhum = (float(row[12]))*(areadict[subflux]/subwatarea)
                precip = (float(row[3]))*.001*(areadict[subflux]/subwatarea) #note precip is averaged here in mm not vol!
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
                wklyradiation.append(sum(radiations[startwk[wkcnt]:endwk[wkcnt]])/daysinweek)

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

        #Write out WEAP Data
        for watershed in (watlist):
            if subwat.startswith(watershed):

                try:
                    os.makedirs("E:\\Hydra\\VIC\\VWEAP_Data\\"+watershed+"_Regulated_VIC\\DATA_WEEKLY"+location+"\SRE"+atm+"_"+scenario+"\\Climate")
                    os.makedirs("E:\\Hydra\\VIC\\VWEAP_Data\\"+watershed+"_Regulated_VIC\\DATA_WEEKLY"+location+"\SRE"+atm+"_"+scenario+"\\Inflows")

                except:
                    print "error creating directories"


                csvwriterweap = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Inflows\\'+subwat+"_Flow_to_River.csv", "wb"))
                csvwriterweaprelhum = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Climate\\'+subwat+"_Humidity.csv", "wb"))
                csvwriterweapradiation = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Climate\\'+subwat+"_Net_Incoming_Radiation.csv", "wb"))
                csvwriterweapprecip = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Climate\\'+subwat+"_Precipitation.csv", "wb"))
                csvwriterweaptemp = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Climate\\'+subwat+"_Temperature.csv", "wb"))
                csvwriterweapwind = csv.writer(open('E:\\Hydra\\VIC\\VWEAP_Data\\'+watershed+'_Regulated_VIC\\DATA_WEEKLY'+location+'\\SRE'+atm+'_'+scenario+'\\Climate\\'+subwat+"_Wind.csv", "wb"))

                csvwriterweap.writerow(([";"+subwat+" "+atm+" "+scenario+" Flow_to_River (m^3)"]))
                for j in range(7800):
                    csvwriterweap.writerow((wklyyr[j],wklydates[j],wklyflowstoriver[j]))

                csvwriterweaprelhum.writerow(([";"+subwat+" "+atm+" "+scenario+" Humidity (%)"]))
                for k in range(7800):
                    csvwriterweaprelhum.writerow((wklyyr[k],wklydates[k],wklyrelhum[k]))

                csvwriterweapradiation.writerow(([";"+subwat+" "+atm+" "+scenario+" Radiation (W/m^2)"]))
                for k in range(7800):
                    csvwriterweapradiation.writerow((wklyyr[k],wklydates[k],wklyradiation[k]))

                csvwriterweapprecip.writerow(([";"+subwat+" "+atm+" "+scenario+" Precipitation (m/wk)"]))
                for l in range(7800):
                    csvwriterweapprecip.writerow((wklyyr[l],wklydates[l],wklyprecip[l]))

                csvwriterweaptemp.writerow(([";"+subwat+" "+atm+" "+scenario+" Temperature (oC)"]))
                for m in range(7800):
                    csvwriterweaptemp.writerow((wklyyr[m],wklydates[m],wklyairtemp[m]))

                csvwriterweapwind.writerow(([";"+subwat+" "+atm+" "+scenario+" Wind (m/s)"]))
                for n in range(7800):
                    csvwriterweapwind.writerow((wklyyr[n],wklydates[n],wklywind[n]))






