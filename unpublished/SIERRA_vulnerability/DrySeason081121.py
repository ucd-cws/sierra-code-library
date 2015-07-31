# ---------------------------------------------------------------------------
#
# Summary : This script processes WEAP csv output data into the metrics of
#           the Index of Hydrologic Vulnerability (IHV).
#
# Author  : Alexandra Geddes
# Version : Nov 14, 2008
#
# Notes:
#   What it does: Reads in the WEAP pourpoint or catchment reported hydrology from .csv files
#               Generates annual, summary, dry years, baseflow, and RecessionLimb metric values
#               Normalizes against T0 for alteration values
#               Writes to output database
#
#   Things which must be in the right place for it to work:
#      NB: most of these should all be in the folder IHV_Bundle where this script lives
#        Input csv files (currently read from Hydra drive)
#        Lookup DB for the upstream topology
#        Output database with empty IHV_Metrics (and possibly DryYears) table
#        seperate IHV_Vulnerability script which pnigs the output db and gives V values
#
#   Random notes:
#        Some names changed during the writing process.
#            metrics = parameters, so they're indexed with m, p, Param, etc
#            locations = pour points, loc, pp, PP
#        To write out intermediate calculations (like the aggregated snowmelt or the
#           actual years considered dry years), there's a variable called 'write' at
#           the beginning of the sub which generates those values.
#
#   Future Work:
#       Non-PourPoint: I set in 3 options for the locations of interest, called 'Aggregation'.
#             - Runs for PP (pourpoints)
#             - It's mostly there but needs to be cleaned up a bit for catchment (reporting
#             the metric values for each individual sub-band the WEAP calculates)
#                eg: QTotal, input csv formats, a few other things
#             - Intermediate would aggregate the WEAP catchment hydrology based on some as-yet
#             to-be-created GIS output reporting the relative contributions of those WEAP
#             catchments to intermediate points.  It's not set up.
#       Summary metrics: only write out once, not same for every year.
#       Special cases for the Alterations values for
#            - threshold parameters (like zero-flow)
#            - params that are 0 in T=0 scenario (again like zero-flow)
#       GUI for the user to input:
#           - file locations of input .csv files, output and lookup databases
#           - What to write and not write (it's currently controled as variables in
#           the subrutines)
#       PointFmCatch:
#           - minor: catchlist indices generation could go somewhere else,
#                   to not have to be done twice
#       LogFile of errors
#
# ---------------------------------------------------------------------------

# Import system modules
from numpy import *
import sys
import win32com.client
import ceODBC as odbc

# Script Debugging
debug = 0

#Function - Whether it will report by pour points, by catchment, or by intermediate points
# 'PP' 'catchment' 'intermediate'
Aggregation = 'PP'

#Explaination of some data structures -
    #HydData[wateryear, week, pourpoint] - array holding WEAP weekly Qs
    #AnnualsLoop[list of arrays[wateryear, parameter, pourpoint]]
    #AlterationsLoop[list of arrays[wateryear, parameter, pourpoint]]
    #Parameters[wateryear, parameter, pourpoint, Scenario1, Scenario2]
        # array of values (on diagonal) and alterations (above diagonal)
    # DryYearsStringsMatrix[scenario,location] - list of list of strings
            # NB: Most of the arrays go location, scenario.  This one's reversed.  Sorry.
        # written out list of dry years at each location, under each scenario.
        # no alterations
        # can't go into Parameters (only takes floats)

#OutputDB = 'C:\Documents and Settings\Alex\My Documents\PhysicalHabitatMetrics\Python\IHV_Working.mdb'
# WEAP input data directory.
drive_letter = 'C:'
in_dir = "H:\WEAP_HYDROLOGY_GIS\WEAP_Output\Results_" # + Scenario + "_deg"
IHV_dir = "C:\Documents and Settings\Alex\My Documents\PhysicalHabitatMetrics\Python\IHV_Bundle"
IntermediateResults = IHV_dir + '\\IntermediateResults'
OutputDB = IHV_dir + '\\IHV_Output\IHV_Output.mdb'
DryYearDB = IHV_dir + '\\IHV_Output\IHV_DryYears.mdb'
LookupDB = IHV_dir + '\\LookupTablesWEAP.mdb'

# Variables
dQcutoff = -0.3 # for determination of beginning of dry season

# Loop Arrays
#Basins = ['KNG']
Basins = ['AMR', 'CAL', 'FEA', 'KAW', 'KNG', 'KRN', 'MER', 'MOK', 'SJN', 'STN', 'TUL', 'TUO', 'YUB']
#AnnualParamLoop = ['LowFlow']
AnnualParamLoop = ['AnnualMean', 'QAnnual', 'CentroidTiming', 'LowFlow', 'HighFlow', 'WeekHighFlow', \
'LowVsHigh', 'NoFlowDur']
SumParamLoop = ['DroughtResistance', 'Q2', 'NumDryYears']
BaseflowParamLoop = ['BaseFlowStart','BaseFlowEnd','DurBaseFlow', 'Base Flow']
RecLimbParamLoop = ['IfSnowmelt', 'SnowmeltStart', 'SnowmeltEnd', 'SnowmeltPeakQ', \
'SnowmeltPeakDate', 'RecLimbSlope']
MasterParamLoop = AnnualParamLoop + SumParamLoop + BaseflowParamLoop + RecLimbParamLoop
Scenarios = ['T0', 'T2', 'T4', 'T6']

# ----------------------------------------------------------------------------
#   Generate pourpoint-reported input array (eg. Qtotal at pour-points)
# ----------------------------------------------------------------------------
def InputArray(input_csv):
    db = 0 # local debug variable

    if (db): print "Input file:", input_csv

    # Read in the .csv
    data = loadtxt(input_csv, delimiter=',', skiprows = 1, usecols = BasinPPOrder)
    if (db):
        print "1st line of data array:", data[0]

    # take off the sumation line from the end
    deleted = delete(data,-1,0)

    # now parse out the years...
    parsed = split(deleted, 21, axis = 0)

    #stick all into one array (there must be a function that does all this at once...)
    global HydData
    HydData = array(parsed)
    if (db):
        print "Shape of HydData:"
        print shape(HydData)
        print "It should be (21, 52, #PourPoints)"
    if (db):
        print "There, they should be sorted now, and placed into the HydData array."
        print "This should be pour point 1, for wateryear 1983 (so starting week 40, 1982):"
        print HydData[2,:,0]
        print ""
        print input_csv[:3], "pour point flows loaded."


# ----------------------------------------------------------------------------
#   Figure out PourPoint order, so it can be read properly into the data array.
# ----------------------------------------------------------------------------
# The way the WEAP csv files are outputted, the PPs aren't in order.  This should
# generate a list of their order, and then a list of the order in which they should be
# inserted into the array (for use in the loadtxt function).

def PourPointOrder(input_csv):
    db = 0 # local debug variable

    if (db): print "Input file:", input_csv

    # create a list of the order of the pourpoints.
    InFile = open(input_csv,'r')
    CList = InFile.readline().split(',') # 1st row: text PP labels.
    InFile.close()

    ppOrder = [] #reading in the order of the pps from the .csv file
    ppPlace = ['']*len(CList) #empty list, will be order in which to read the columns (pps) into the array
    p = 1 #index (first cell empty in header row)

    CList[-1] = CList[-1][:-1] # remove the last "\n" carrage return.

    while p<len(CList):
        ppOrder = ppOrder + [[p,int(CList[p][-2:])]]
        p=p+1
    for Pair in ppOrder:
        ppPlace[Pair[1]]=Pair[0]
    ppPlace = ppPlace[1:] #remove first empty place (because first cell of label row was empty)
    if (db):
        print "This is the order that the PourPoints are in:", ppOrder
        print "This will be the placement of the columns into the array:", ppPlace
    return ppPlace


# ----------------------------------------------------------------------------
#   Generate Annual Parameter Values array
# ----------------------------------------------------------------------------
def AnnualParamArray():
    db = 0

    # Create empty parameter array Param[year,parameter,pourpoint]
    Param = zeros((HydData.shape[0],len(AnnualParamLoop), HydData.shape[2]))
    if (db): print "Param.shape =", Param.shape

    # Iterate around the HydData array, calculating parameters.
    # indices:
    y = 0   #year 0-20
    p = 0   #parameter, see AnnualParamLoop
    pp = 0  #pour points, depends on baisn, 0-(Hydata.shape[2]-1)
    w = 0   #week 0-52

    if (db): print "starting param looping."
    while p < len(AnnualParamLoop):
        while y < Param.shape[0]:
            while pp < HydData.shape[2]:
                Param[y,p,pp] = AnnualParamValue(y,p,pp)
                if (db): print "within pp loop:", Param[y,p,:]
                pp = pp + 1
            if (db): print "pp loop done. y=",y, "p=", p, Param[y,p,:]
            y = y + 1
            pp = 0
        if (db): print "y loop done.  For WY 1981, parameter:", AnnualParamLoop[p] , "=", Param[0,p,:]
        p = p+1
        y = 0
        
    return Param
    print ""


# ----------------------------------------------------------------------------
#   Annual Parameters - Value Calculations
# ----------------------------------------------------------------------------

# I think these can be done at the array level, rather than by entry.
# Param[:,p,:] = SomeFunction(HydData[WeeksAxis])
def AnnualParamValue(y,p,pp):
    db = 0
    if AnnualParamLoop[p] == 'AnnualMean':
        return HydData[y,:,pp].mean()
    elif AnnualParamLoop[p] == 'QAnnual':
        return HydData[y,:,pp].sum()
    elif AnnualParamLoop[p] == 'CentroidTiming':
        DenomArray = HydData[y,:,pp]*arange(1,53)
        if (db): print "CentroidTiming for y=",y, "pp=",pp, DenomArray.sum()/HydData[y,:,pp].sum()
        return DenomArray.sum()/HydData[y,:,pp].sum()
    elif AnnualParamLoop[p] == 'LowFlow':
        return HydData[y,:,pp].min()
    elif AnnualParamLoop[p] == 'HighFlow':
        return HydData[y,:,pp].max()
    elif AnnualParamLoop[p] == 'WeekHighFlow':
        return HydData[y,:,pp].tolist().index(HydData[y,:,pp].max())
    elif AnnualParamLoop[p] == 'LowVsHigh':
        return HydData[y,:,pp].min()/HydData[y,:,pp].max()
    elif AnnualParamLoop[p] == 'NoFlowDur':
        return HydData[y,:,pp].tolist().count(0.0)

    else:
        print "Couldn't find a calculation in AnnualParamValue for", AnnualParamLoop[p]
        return nan

# ----------------------------------------------------------------------------
#   Summary Parameters
# ----------------------------------------------------------------------------
def SumParams():
    
    db = 0 # local debug variable
    
    # Initialize SumParamArray - only one for whole timeperiod, not yearly
    SumParamArray = zeros((1,len(SumParamLoop), HydData.shape[2]))
    
    # 0: Drought Resistance
    pp = 0
    while pp<HydData.shape[2]:
        SumParamArray[0,0,pp] = HydData[11,:,pp].min()/HydData[6,:,pp].min()
            #Calculates mins for 1987 (y=6) and 1992 (y=11)
        pp = pp+1

    # 1: Q2
        # rank needed = (years of record + 1)/return period = 11
    QmaxIndex = AnnualParamLoop.index('HighFlow')
    QmaxArray = Parameters[:,QmaxIndex,:,i,i] # 2D array of Qmaxs[wateryear,pp]
    QmaxSorted = QmaxArray[QmaxArray.argsort(axis=0)][:,0,:] # sorted QmaxArray
    SumParamArray[0,1,:] = QmaxSorted[-11] # list of 11th highest value for each pp
    
    # 3, 4: DryYears, NumDryYears - uses seperate function, called from main program
    # to also capture T0 list of dry years for the length of dry season.
    
    return SumParamArray

# ----------------------------------------------------------------------------
#   Generate catchment-reported input array
# ----------------------------------------------------------------------------
def CatchmentArray(input_csv):
# Takes WEAP outputs reported by catchment and returns an array of the values
#  and a list of the catchment order.
    db = 0 # local debug variable
    if (db): print "Starting CatchmentArray. \nInput file:", input_csv

    # create a list of the order of the catchments.
    InFile = open(input_csv,'r')
    InList = InFile.readline().split(',') # 1st row: text catchment labels.
    InFile.close()
    CList = []
    for item in InList:
        CList = CList + [item.strip()]
    if (db): print "Order of Catchments:", CList[1:-1] #to remove 1st column (blank) and last column (sums)

    # Read in the .csv
    data = loadtxt(input_csv, delimiter=',', skiprows = 1, usecols = arange(1,len(CList)-1))
    if (db):
        print "1st row of data:", data[0]

    # take off the sumation line from the end
    deleted = delete(data,-1,0)

    # now parse out the years...
    parsed = split(deleted, 21, axis = 0)

    #stick all into one array (there must be a function that does all this at once...)
    CatchData = array(parsed)
    if (db):
        print "Shape of CatchData:", CatchData.shape
        print " -(For MOK it should be (21, 52, 56) )" #there's a "sum" column at the end which should be excluded.
    if (db):
        print "This should be the first column, for wateryear 1983 (so starting week 40, 1982):"
        print CatchData[2,:,0]
        print ""
        print input_csv[:3], "catchment-reported model-data loaded."
    return CatchData, CList[1:-1]

# ----------------------------------------------------------------------------
#   Calculate values at points based on values reported by WEAP "catchment"
# ----------------------------------------------------------------------------
def PointFromCatch(catchcsv):
# Returns aggregated values into PointCatchArray[year,week,pourpoint] from a given csv
# file of 'catchment'-reported values.  Uses PPContribs (list of lists of relivant topology)
# and adds up the contributing catchments to each pourpoint.
# Option to write the pourpoint values to another csv.

    db = 0 # local debug variable
    write = 0 # whether if should write out the results to a csv file.

    if (db): print "Starting PointFromCatch"

    # Initialize results array
    PointCatchArray = zeros((HydData.shape)) #Weekly accumulated values [year,week,pourpoint]

    # generate data Array and List of catchment names
    CatchData, CatchList = CatchmentArray(catchcsv)
    # CatchData is a data array[year,week,catchment] - from CatchmentArray
    # CatchList is a list of the string names of the catchments. - from CatchmentArray

    # For each PP, add up the contributing catchments.
    pp=0
    while pp < PointCatchArray.shape[2]:
        # List of upslope objects (from PPContribs list of lists)
        ContribList = PPContribs[pp] # all upstream objects in WEAP topology
        #Translate into a list of indices to be called
        CatchIndex = []
        for entry in ContribList:
            if entry in CatchList: # Catchlist is the list of catchments, in the order they appear
                CatchIndex += [CatchList.index(entry)]
        # Report contributing catchments
        if (db):
            ContribNames = []
            for Ind in CatchIndex:
                ContribNames += [CatchList[Ind]]
            print Basin + '_' + str(pp+1) + ':', ContribNames
        #Aggregate for each year/week
        y = 0
        while y < PointCatchArray.shape[0]:
            w = 0
            while w<PointCatchArray.shape[1]:
                PointCatchArray[y,w,pp] = CatchData[y,w,CatchIndex].sum()
                w=w+1
            y=y+1
        pp = pp+1

    #to write results to file
    if (write):
        PrintArray = hstack(array_split(PointCatchArray,21))[0,:,:]
        PrintName = IntermediateResults + '\\PP_'+catchcsv[48:]
        print "Writing PointCatchArray to csv file:", PrintName, "shape:", PrintArray.shape
        savetxt(PrintName, PrintArray, delimiter = ',', fmt='%f')

    return PointCatchArray

# ----------------------------------------------------------------------------
#   Ping the Lookup DB to get the list of contributing upstream catchments
# ----------------------------------------------------------------------------
def GetContribList(pp):
# Mostly lifted from HPSA_Update.py, by Mike Byrne.  Thanks.

    db = 0 # local debug variable
    if (db): print "Starting GetContribList"

    engine = win32com.client.Dispatch("DAO.DBEngine.36")
    myDB = engine.OpenDatabase(LookupDB)

    Digits = pp+1
    if Digits<10:
        Digits = '0' + str(Digits)
    else:
        Digits = str(Digits)

    if (db): print Digits

    qryUpCatchs = "SELECT PPNames.PourPoint_id, UpstreamPoints_"+Basin+".UPSTRMNM "
    qryUpCatchs += "FROM PPNames INNER JOIN UpstreamPoints_"+Basin+" ON PPNames.out_name = UpstreamPoints_"+Basin+".DNSTRMNM "
    qryUpCatchs += "WHERE (((PPNames.PourPoint_id)='" +Basin+ "_" + Digits + "'));"

    rs = myDB.OpenRecordset(qryUpCatchs)
    UpCatchList = []
    while not rs.EOF:
        UpCatchList = UpCatchList + [str(rs.Fields("UPSTRMNM").Value)]
        rs.MoveNext()
    del rs

    return UpCatchList

# ----------------------------------------------------------------------------
#   Duration of Base Flow
# ----------------------------------------------------------------------------
def BaseFlow(catchcsv):
# Calculate the Baseflow parameters.

    db = 0 # local debug variable
    write = 0 # to write out these sub-results to a csv file.

    if (db): print "  - Starting BaseFlow"

    # Initialize results arrays:
    BaseArray = zeros((HydData.shape[0], len(BaseflowParamLoop) ,HydData.shape[2]))
        # Baseflow results: [year, BaseFlow parameters, pourpoints]

    # Get runoff values (reported by WEAP 'catchments')
    if Aggregation == 'PP':
        RunArray = PointFromCatch(catchcsv) #[year,week,pourpoint]
    elif Aggregation == 'catchment':
        RunArray, DontNeedListHere = CatchmentArray(catchcsv) #[year,week,catchment], plus it returns a catchment list.
    if (db):
        print '  - Surface Runoff data from first year of first location (e.g. PP1 or lowest catchment):'
        print RunArray[0,:,0]

    # Beginning of baseflow -
    # Calculate weekly dQ - (deltaQ)/(mean)
        # Create dQarray [year,week,location], same as HydData
    dQArray = zeros((HydData.shape))
        # Populate it, calculating from HydData
    pp = 0
    while pp<dQArray.shape[2]:
        y = 0
        while y<dQArray.shape[0]:
            w = 1 # can't calculate first week of year by this equation.
            while w<dQArray.shape[1]:
                dQArray[y,w,pp] = (HydData[y,w,pp]-HydData[y,w-1,pp])/ \
                ((HydData[y,w,pp]+HydData[y,w-1,pp])/2)
                w += 1
            # first week = second week
                # NB: if we decide to actually start using these dQs for more,
                # the first weeks of all but the first year can be calculated.
            dQArray[y,0,pp] = dQArray[y,1,pp]
            y += 1
        pp += 1
    # ******* Some annual index of the weekly rates of change?  To add into ParamArray.

    if db:
        print ' - Weekly dQ calculated.  For 1981, location 1: \n', dQArray[0,:,0]
        print ' - Calculating BaseFlow metrics.'
        
    print ' - ', Basin, Scenarios[i], ' - BaseFlow metric calculation errors:'
    pp = 0
    while pp<RunArray.shape[2]:
        y = 0
        while y<(RunArray.shape[0]): # can't calculate BaseFlow for last year, but still
                                        #need begin date for reccession limb slope.
            # BaseFlowBegin = Count backwards from sept1 (week 49) to first dQ < dQcutoff
                # NB: the cut-off is arbitrary.  It just kinda looked right on a few sample PPs
                # There are lots of problems...
            w = 49
            while w>=23:
                if dQArray[y,w,pp] >= dQcutoff and dQArray[y,w-1,pp] < dQcutoff:
                    BaseArray[y,0,pp] = w
                    break
                w = w-1
            if BaseArray[y,0,pp] == 0:
                print " * BaseFlow begin, ", 1981+y, ", location ", pp+1
                BaseArray[y,0,pp] = nan
            if y<(RunArray.shape[0]-1):  # don't capture baseflow end for last year
                # BaseFlowEnd
                # Working back from week 15 of the following wateryear
                w = 15
                while w>=0:
                    if RunArray[y+1,w,pp] == 0 and RunArray[y+1,w+1,pp] != 0 and RunArray[y+1,w+2,pp] != 0:
                        BaseArray[y,1,pp] = 52+ (w+1)
                        break
                    w = w-1
                # week 0
                if BaseArray[y,1,pp] == 0: # so it's still the zero it was created with
                    if RunArray[y,-1,pp] == 0 and RunArray[y+1,0,pp] != 0 and RunArray[y+1,1,pp] != 0:
                        BaseArray[y,1,pp] = 52
                # w = 51 (last week of current wateryear)
                if BaseArray[y,1,pp] == 0:
                    if RunArray[y,-2,pp] == 0 and RunArray[y,-1,pp] != 0 and RunArray[y+1,0,pp] != 0:
                        BaseArray[y,1,pp] = 51
                # w=50 down to beginning you calculated before
                if BaseArray[y,1,pp] == 0:
                    w = 51
                    if BaseArray[y,0,pp] == nan: BFBegin = 23 # So you can still calc the end of baseflow
                    else: BFBegin = BaseArray[y,0,pp]
                    while w >= BFBegin + 3:
                        if RunArray[y,w-2,pp] == 0 and RunArray[y,w-1,pp] != 0 and RunArray[y,w,pp] != 0:
                            BaseArray[y,1,pp] = (w-1)
                            break
                        w = w-1
                # and if you -still- got nothing, then it didn't work.
                if BaseArray[y,1,pp] == 0:
                    print " * BaseFlow end, ", 1981+y, ", location ", pp+1
                    BaseArray[y,1,pp] = nan

                # calculate baseflow (average Qtotal during BaseFlow period)
                if BaseArray[y,0,pp] != nan and BaseArray[y,1,pp] != nan:
                    if BaseArray[y,1,pp] > 51:
                        BaseQtotal = append(HydData[y,BaseArray[y,0,pp]:,pp], HydData[y+1,:(BaseArray[y,1,pp]-52),pp])
                    else:
                        BaseQtotal = HydData[y,BaseArray[y,0,pp]:BaseArray[y,1,pp],pp]
                    BaseArray[y,3,pp] = BaseQtotal.mean()

            y = y+1
        pp = pp+1

            # calculate duration of baseflow
    BaseArray[:,2,:] = BaseArray[:,1,:] - BaseArray[:,0,:]

    #to write results to file
    if (write):
        PrintArray = hstack(array_split(BaseArray,21))[0,:,:]
        PrintName = IntermediateResults + '\\BaseFlow_' + Basin + '_' + Scenarios[i] + '.csv'
        print "Writing BaseArray to csv file:", PrintName, "shape:", PrintArray.shape
        savetxt(PrintName, PrintArray, delimiter = ',', fmt='%f')

    return BaseArray

# ----------------------------------------------------------------------------
#   Identify dry years
# ----------------------------------------------------------------------------
def DryYears():
# Identify the dry years for that basin, an index list for each location, under base scenario
# Return: list of lists of indexes to dry years[location] list of NumDryYears[location],
# list of strings naming those dry years[location]

    db = 0 # local debug variable
    write = 0 # whether to srite out the dry years to DryYearDB

# Find index of annual QTotal withing the ParamArray
    QT = MasterParamLoop.index('QAnnual')

# Cycle through the locations in that basin, adding to DryYearIndexLists
    DryYearsIndexLists = []
    NumDryYearsList = []
    DryYearsStrings = []
    pp = 0
    while pp < HydData.shape[2]:
    # Calculate the mean QTotal
        QTmedian = median(Parameters[:, QT, pp, 0, 0])
    # Create index list of years when QTotal<QTotalMean
        DryYears = []
        DryYearsString = ''
        y = 0
        while y < HydData.shape[0]:
            if Parameters[y, QT, pp, i, i] < QTmedian:
                DryYears += [y]
                DryYearsString += str(y + 1981) + ' '
            y += 1
    # Add it to the list of lists, count up num dry years
        DryYearsIndexLists += [DryYears]
        NumDryYearsList += [len(DryYears)]
        DryYearsStrings += [DryYearsString.strip()]

        pp += 1

    if (write):
        #Write dry years out to DryYears database
        if (debug): print "Writing dry years to DB."
        WriteDryYearsToDB()
        if (debug): print "Written."

    return DryYearsIndexLists, NumDryYearsList, DryYearsStrings

# ----------------------------------------------------------------------------
#   Recession Limb Slope
# ----------------------------------------------------------------------------
def RecessionLimb(catchcsv):
# Calculate the Recession Limb Slope parameters.

    db = 0 # local debug variable
    write = 0 # to write out these sub-results to a csv file.

    if (db): print "  - Starting RecessionLimb"

    # Initialize results arrays:
    RecLimbArray = zeros((HydData.shape[0], len(RecLimbParamLoop) ,HydData.shape[2]))
        # RecessionLimb results: [year, RecessionLimb parameters, pourpoints]

    # Get Snowmelt values (reported by WEAP 'catchments')
    if Aggregation == 'PP':
        SnowmeltArray = PointFromCatch(catchcsv) #[year,week,pourpoint]
    elif Aggregation == 'catchment':
        SnowmeltArray, DontNeedListHere = CatchmentArray(catchcsv) #[year,week,catchment]
    if (db):
        print '  - Snowmelt data from first year of first location (e.g. PP1 or lowest catchment):'
        print SnowmeltArray[0,:,1]

    pp = 0
    while pp<SnowmeltArray.shape[2]:
        y = 0
        if db: print y,pp
        while y<(SnowmeltArray.shape[0]):

            # 0: 'IsSnowMelt'
            if db: print "0:",y,pp
            if SnowmeltArray[y,:,pp].sum() == 0:
                RecLimbArray[y,0,pp] = 0
                RecLimbArray[y,1:,pp] = 0 # so it'll give a 100% change if there was snowmelt before.
            else:
                RecLimbArray[y,0,pp] = 1

                # 1: 'SnowmeltBegin'
                if db: print "1:" ,y,pp
                w = 0
                while w < SnowmeltArray.shape[1]:
                    if SnowmeltArray[y,w,pp] !=0:
                        RecLimbArray[y,1,pp] = w
                        break
                    w = w+1

                # 2: 'SnowmeltEnd'
                if db: print "2:",y,pp
                w = SnowmeltArray.shape[1] - 1
                while w > 0:
                    if SnowmeltArray[y,w,pp] !=0:
                        RecLimbArray[y,2,pp] = w + 1
                        break
                    w = w-1

                # 3: 'PeakQ'
                if db: print "3:",y,pp
                RecLimbArray[y,3,pp] = \
                 HydData[y, int(RecLimbArray[y,1,pp]):int(RecLimbArray[y,2,pp]) ,pp].max()

                # 4: Week of peak snowmelt
                if db: print "4:",y,pp
                RecLimbArray[y,4,pp] = HydData[y,:,pp].tolist().index(RecLimbArray[y,3,pp])

            y = y+1
        pp = pp+1

    # 5: Recession Limb Slope
    # (BaseFlow - PeakSnowmeltFlow)/(BeginBaseflowWeek-PeakSnowmeltWeek)
    if db: print "5:"
    BF = MasterParamLoop.index('Base Flow')
    BFS = MasterParamLoop.index('BaseFlowStart')
   
    RecLimbArray[:,5,:] = (Parameters[:,BF,:,i,i]-RecLimbArray[:,3,:])/(Parameters[:,BFS,:,i,i]-RecLimbArray[:,4,:])

    #to write results to file
    if (write):
        PrintArray = hstack(array_split(RecLimbArray,21))[0,:,:]
        PrintName = 'RecLimb_' + Basin + '_' + Scenarios[i] + '.csv'
        print "Writing RecLimbArray to csv file:", PrintName, "shape:", PrintArray.shape
        savetxt(PrintName, PrintArray, delimiter = ',', fmt='%f')

    return RecLimbArray

# ----------------------------------------------------------------------------
#   List of SiteNames for that basin.
# ----------------------------------------------------------------------------
def GenSiteNames():

    db = 0 # local debug variable

    SiteNamesList = []
    SiteName = ''
    BasinName = ''

    if Aggregation == 'PP':
        loc = 0
        while loc < HydData.shape[2]:
            Digits = loc+1
            if Digits<10:
                Digits = '0' + str(Digits)
            else:
                Digits = str(Digits)
            SiteNamesList += [Basin+"_"+Digits]
            loc += 1
        # Pull out COS
        if Basin == 'AMR':
            loc = len(SiteNamesList)-5
            Cos = 1
            while loc < len(SiteNamesList):
                SiteNamesList[loc] = 'COS_0' + str(Cos)
                Cos += 1
                loc += 1
        # Pull out BAR
        elif Basin == 'YUB':
            loc = len(SiteNamesList)-6
            Bar = 1
            while loc < len(SiteNamesList):
                SiteNamesList[loc] = 'BAR_0' + str(Bar)
                Bar += 1
                loc += 1
    else:
        # like Aggregation == 'catchment' or something else:
        print "****************** \nWoah, woah... SiteNames \
        for Aggregation or Intermediate algorythms not yet coded!! \n*********************"
        loc = 0
        while loc < HydData.shape[2]:
            SiteNamesList += [Basin + '_??']
            loc += 1

    return SiteNamesList

# ----------------------------------------------------------------------------
#   Write Metric Values to Database
# ----------------------------------------------------------------------------
def WriteParamToDB(DataArray):
    # Loops through each Wateryear/Point/Index combination, and writes a line to the DB table
    # with all the various index and alteration values

    db = 0 # local debug variable

    # Generate list of SiteNames
    SiteNames = GenSiteNames()

    # connect to database
    conn = odbc.Connection(
        "Driver={Microsoft Access Driver (*.mdb)};Dbq=" + OutputDB + ";Uid=Admin;Pwd=;")
    crs = conn.cursor()

    # Columns in database, as of 7-5-08:
    ColumnList = ['Site', 'Wateryear', 'Metric', 'T00', 'A02', 'A04', 'A06', 'T02', 'A24', 'A26', 'T04', 'A46', 'T06']

    y,p,pp = 0,0,0
    while y<DataArray.shape[0]:
        while p< DataArray.shape[1]:
            while pp< DataArray.shape[2]:

                if (db):
                    print "Generate lists"
                TableList = []
                # site:
                TableList += [SiteNames[pp]]
                # wateryear
                if y < (DataArray.shape[0]-2):
                    TableList += [str(1981 + y)]
                elif y == (DataArray.shape[0]-2):
                    TableList += ['Mean']
                else:
                    TableList += ['StdDev']
                # parameters
                TableList += [MasterParamLoop[p]]
                # Scenario and alteration values
                sc1 = 0
                sc2 = 0
                while sc1 < len(Scenarios):
                    while sc2 < len (Scenarios):
                        if sc1 <= sc2:
                            TableList += [Parameters[y,p,pp,sc1,sc2]]
                        sc2 += 1
                    sc1 += 1
                    sc2 = 0

                TableTuple = tuple(TableList) # oops, execute command wants ()

                if db:
                    print "TableList:", TableList
                    print "ColumnList:", ColumnList

                # Generate SQL command
                SQLString = "insert into IHV_Metrics ("
                for col in ColumnList:
                    SQLString += col + ","
                SQLString = SQLString[:-1] + ") values (" + "?,"*(len(ColumnList)-1) + "?)"
                if db: print SQLString

                # Write that line
                if db: print "Write line to database table"
                crs.execute(SQLString,TableTuple)

                pp += 1
            p += 1
            pp = 0
        y +=1
        p = 0
        pp = 0

    conn.commit()
    conn.close()

# ----------------------------------------------------------------------------
#   Write Dry Years to Database
# ----------------------------------------------------------------------------
def WriteDryYearsToDB():
    # Loops through each Wateryear/Point combination, and writes a line to the DB table
    # with the scenarios for which that's a dry year listed under each year.

    db = 0 # local debug variable

    # connect to database
    conn = odbc.Connection(
        "Driver={Microsoft Access Driver (*.mdb)};Dbq=" + DryYearDB + ";Uid=Admin;Pwd=;")
    crs = conn.cursor()

    # Columns in database, as of 7-5-08:
    ColumnList = ['Site', '1981', '1982', '1983', '1984', '1985', '1986', '1987', '1988', '1989', \
    '1990', '1991', '1992', '1993', '1994', '1995', '1996', '1997', '1998', '1999', '2000', '2001']

    pp = 0
    while pp< HydData.shape[2]:
        if (db):
            print "Generate TableList"
        TableList = ['','','','','','','','','','','','','','','','','','','','','','',]
        # site:
        if Aggregation == 'PP':
            Digits = pp+1
            if Digits<10:
                Digits = '0' + str(Digits)
            else:
                Digits = str(Digits)
            TableList[0] = Basin+"_"+Digits
##                elif Aggregation == 'catchment':
##                    TableList += [PlaceNames[pp]]
        # each wateryear
        y = 0
        while y<HydData.shape[0]:
            sc = 0
            while sc < len(Scenarios):
                if y in DryYearsMatrix[sc][pp]:
                    TableList[y+1] += Scenarios[sc] + ' '
                sc += 1
            TableList[y+1] = TableList[y+1].strip()
            if TableList[y+1] == '': TableList[y+1] = 'none'
            y+=1

        # write to DB

        TableTuple = tuple(TableList) # execute command wants ()

        if db:
            print "TableList:", TableList
            print "ColumnList:", ColumnList

        # Generate SQL command
        SQLString = "insert into DryYears ("
        for col in ColumnList:
            SQLString += col + ","
        SQLString = SQLString[:-1] + ") values (" + "?,"*(len(ColumnList)-1) + "?)"
        if db: print SQLString

        # Write that line
        if db: print "Write line to database table"
        crs.execute(SQLString,TableTuple)

        pp+=1

    conn.commit()
    conn.close()

# ----------------------------------------------------------------------------
#   Main - Start program
# ----------------------------------------------------------------------------

print "starting...\n"
debugLoops = 0 # local debug variable for loop generation.

for Basin in Basins:
    print "** Basin:", Basin, '\n'
    print "Generating iteration loops:"
    QLoop = []
    RunoffLoop = []
    SnowmeltLoop = []
    for scen in Scenarios:
        if Aggregation == 'PP': QLoop += [in_dir + scen[-1] + "_deg\\" + \
        Basin + '_PourPoints_DeltaT_' + scen[-1] + '.csv']
        # not updated: if Aggregation == 'catchment': QLoop += [Basin + '_FlowtoRiver_DeltaT= ' + scen[-1] + '.csv']
        RunoffLoop += [in_dir + scen[-1] + "_deg\\" + \
        Basin + '_SurfaceRunoff_DeltaT_' + scen[-1] + '.csv']
        SnowmeltLoop += [in_dir + scen[-1] + "_deg\\" + \
        Basin + '_SnowMelt_DeltaT_' + scen[-1] + '.csv']
    if (debugLoops):
        print 'TotalQ filenames:', QLoop
        print 'Runoff filenames:', RunoffLoop
        print 'Snowmelt filenames:', SnowmeltLoop

    DryYearsStringsMatrix = []

    if Aggregation == 'PP':
        BasinPPOrder = PourPointOrder(QLoop[0])
        PPContribs = []
        PP = 0
        while PP<len(BasinPPOrder):
            PPContribs += [GetContribList(PP)]
            PP +=1
    try:
        # loop through scenarios, generating first the QTotal-based parameters,
        #   then the catchment-reported parameters
        i = 0
        while i<len(QLoop):
            if (debug):
                print '\n', QLoop[i]
            if Aggregation == 'PP': InputArray(QLoop[i]) #loads the QTotal data into HydData array
            elif Aggregation == 'catchment':
                HydData, PlaceNames = CatchmentArray(QLoop[i])
                # HydData[year,week,catchment], PlaceNames list of textnames of catchments
            if (debug):
                print "QTotal data loaded."
                print "Check: Week 42, 1984, location 1 =", HydData[4,2,0]
            # Initialize Parameters array - needs to happen after the HydData is in place, to know dimensions
            if i == 0:
                print "Initializing Parameters array."
                Parameters = zeros((HydData.shape[0], len(MasterParamLoop), HydData.shape[2], \
                    len(Scenarios), len(Scenarios)))
                    # array of values under each scenario (on diagonal) and alterations
                        #[wateryear, parameters, pourpoint, Scenario1, Scenario2]

            # Annual Parameters
            if (debug): print "Running AnnualParamArray."
            Parameters[:,:len(AnnualParamLoop),:,i,i] = AnnualParamArray()
            
            # Summary Parameters
            if (debug): print 'Running SumParams.'
            Parameters[:,len(AnnualParamLoop):(len(AnnualParamLoop)+len(SumParamLoop)),:,i,i] = SumParams()
                # Same summary value entered for every year.

            # Dry years - index list for BaseFlow calcs and NumDryYears
            if (debug): print "Calculating DryYears."
            DryIndexLists, NumDryYearsList, DryYearsListOfStrings = DryYears()
            if i == 0:
                DryLists = DryIndexLists # for calculation of BaseFlow mean/stddev values
                    # DryLists[location] = lists of wateryear indices which were dry years in T0 scenario
            Parameters[:,MasterParamLoop.index('NumDryYears'),:,i,i] = NumDryYearsList
                # Dry Years written out only if 'write' variable it true within the
                #    'DryYears' function above
            DryYearsStringsMatrix += [DryYearsListOfStrings]
            DryYearsMatrix += [DryIndexLists] #[scenario][pp]

            # Baseflow parameters
            if (debug): print "Running BaseFlow."
            Parameters[:,(len(AnnualParamLoop)+len(SumParamLoop)):(len(AnnualParamLoop)+len(SumParamLoop)+len(BaseflowParamLoop)),:,i,i] = BaseFlow(RunoffLoop[i])

            # Recession Limb Parameters
            if (debug): print "Running RecessionLimb."
            Parameters[:,(len(AnnualParamLoop)+len(SumParamLoop)+len(BaseflowParamLoop)):,:,i,i] = RecessionLimb(SnowmeltLoop[i])
            
            if (debug):
                print "Parameter values array for T=" + str(i*2) + " generated."
                print 'Check: Mean flow past first location in wy1981 under this scenario =', \
                 Parameters[0,0,0,i,i]
            i=i+1

        # generate Alterations
        if (debug):
            print "\nGenerating Alteration values."
        for S1 in range(len(Scenarios)):
            for S2 in range(len(Scenarios)):
                if S1 < S2:
                    Parameters[:,:,:,S1,S2] = (Parameters[:,:,:,S2,S2] - Parameters[:,:,:,S1,S1]) \
                        / Parameters[:,:,:,S1,S1] # higher deltaT normalized against lower deltaT.

        # Averages and Std Deviations.
        if (debug): print '\nGenerating averages and standard deviations.'
        Parameters = append(Parameters,Parameters[:21,:,:].mean(axis=0)[newaxis,:,:],0)
        Parameters = append(Parameters,Parameters[:21,:,:].std(axis=0)[newaxis,:,:],0)

        # Recalc BaseFlow mean/stddev
        # mean, stddev - only for dry years.
        if (debug): print "\n Recalculating DurBaseFlow avg/std for dry years only."
        BFi = MasterParamLoop.index(BaseflowParamLoop[0])
        BFf = MasterParamLoop.index(BaseflowParamLoop[-1])
        pp = 0
        while pp<HydData.shape[2]:
            Parameters[-2,BFi:BFf+1,pp,:,:] = Parameters[DryLists[0],BFi:BFf+1,pp,:,:].mean(axis=0)
            Parameters[-1,BFi:BFf+1,pp,:,:] = Parameters[DryLists[0],BFi:BFf+1,pp,:,:].std(axis=0)
            if (debug):
                print Basin + "_" + str(pp+1) + ":"
                print "  Avg:", Parameters[-2,BFi,pp,:,:]
                print "  Std:", Parameters[-1,BFi,pp,:,:]
            pp += 1

        # write metrics outputs.
        print "\n", Basin, "- Writing metric values and alterations to database table (this may take a while)."
        WriteParamToDB(Parameters)
        if (debug): print "Written."

    except:
        print sys.exc_info()[1]
        print "Darn.  Aborted."

print "end end"
        
print ""
