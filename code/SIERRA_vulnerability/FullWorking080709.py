# ---------------------------------------------------------------------------
#
# Summary : This script is designed to process WEAP output data into Indices
#           of Hydrologic Vulnerability.
#
# Author  : Alexandra Geddes
# Version : July 9, 2008
#
# Notes   : So far it successfully:
#               Reads in the WEAP pourpoint hydrology
#               Generates annual, summary, baseflow, and RecessionLimb parameter values
#               Normalizes against T0 for alteration values
#               Calculate out an overall Vulnerability
#               Write to database IHV_Working, tables: IHV_ParemeterData, IHV_Vulnerability
#
#           Still need to:
#               Special cases for threshold parameters (like zero-flow)
#                   for params that are 0 in T=0 scenario (again like zero-flow)
#               file locations of input .csv files
#               name/location of output database/table
#
# ---------------------------------------------------------------------------

# Import system modules
from numpy import *
import sys
import win32com.client
import ceODBC as odbc

# Script Debugging
debug = 1

# Global variables
    #HydData[wateryear, week, pourpoint] - array holding WEAP weekly Qs
    #AnnualsLoop[list of arrays[wateryear, parameter, pourpoint]]
    #AlterationsLoop[list of arrays[wateryear, parameter, pourpoint]]
    #Parameters = zeros((HydData.shape[0],len(AnnualParamLoop), HydData.shape[2], \
        #NumberScenarios, NumberScenarios))
        # array of values (on diagonal) and alterations (above diagonal) [wateryear, parameter, pourpoint, Scenario1, Scenario2]
        # to replace AnnualsLoop and AlterationsLoop
WriteToFolder = 'JunkOutput/' #not coded in
OutputDB = 'C:\Documents and Settings\Alex\My Documents\PhysicalHabitatMetrics\Python\IHV_Working.mdb'
LookupDB = "C:\Documents and Settings\Alex\My Documents\PhysicalHabitatMetrics\WEAP\LookupTables\LookupTablesWEAP.mdb"


# Local variables

# Loop Arrays
Basins = ['CAL']
#Basins = ['AMR', 'CAL', 'FEA', 'KAW', 'KNG', 'KRN', 'MER', 'MOK', 'SJN', 'STN', 'TUL', 'TUO', 'YUB']
#AnnualParamLoop = ['LowFlow']
AnnualParamLoop = ['AnnualMean', 'CentroidTiming', 'LowFlow', 'HighFlow', 'WeekHighFlow', \
'LowVsHigh', 'NoFlowDur']
SumParamLoop = ['DroughtResistance', 'Q2']
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

    # create a list of the order of the pourpoints.
    InFile = open(input_csv,'r')
    CList = InFile.readline().split(',') # 1st row: text PP labels.
    InFile.close()

    ppOrder = [] #reading in the order of the pps from the .csv file
    ppPlace = ['']*len(CList) #empty list, will be order in which to read the columns (pps) into the array
    p = 1 #index (first cell empty in header row)

    CList[-1] = CList[-1][:-1] # remove the last "\n"

    while p<len(CList):
        ppOrder = ppOrder + [[p,int(CList[p][-2:])]]
        p=p+1
    for Pair in ppOrder:
        ppPlace[Pair[1]]=Pair[0]
    ppPlace = ppPlace[1:] #remove first empty place (because first cell of label row was empty)
    if (db):
        print "This is the order that the PourPoints are in:", ppOrder
        print "This will be the placement of the columns into the array:", ppPlace

    # Read in the .csv
    data = loadtxt(input_csv, delimiter=',', skiprows = 1, usecols = ppPlace)
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
#   Generate Annual Parameter Values array
# ----------------------------------------------------------------------------
def AnnualParamArray():
    db = 0

    # Create empty parameter array Param[year,parameter,pourpoint]
    Param = zeros((HydData.shape[0],len(AnnualParamLoop), HydData.shape[2]))
    if (db): print "Param.shape =", Param.shape

    # Generate the BaseFlow data.
    #Run the BaseFlow function to generate the BaseResultsArray
    global BaseArray
    BaseArray = BaseFlow

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
    if (db): print "Order of Catchments:", CList[1:-1] #to remove ist column (blank) and last column (sums)

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
#   Calculate values at points based on values reported by "catchment"
# ----------------------------------------------------------------------------
def PointFromCatch(catchcsv):
# Returns aggregated values into PointCatchArray[year,week,pourpoint] from a given csv
# file of 'catchment'-reported values.  Pings a database for relivant topology and adds
# up the contributing catchments to each pourpoint.
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
        # NB: CatchList names start with ' '

    # For each PP, ping the database for topology, then add up the contributing catchments.
    pp=0
    while pp < PointCatchArray.shape[2]:
        #Ping the Database
        ContribList = GetContribList(pp)
        #Translate into a list of indeces to be called
        CatchIndex = []
        for entry in ContribList:
            if entry in CatchList:
                CatchIndex += [CatchList.index(entry)]
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
        PrintName = 'PP_'+catchcsv
        print "Writing PointCatchArray to csv file:", PrintName, "shape:", RunPrint.shape
        savetxt(PrintName, RunPrint, delimiter = ',', fmt='%f')

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
#   Ping the Output DB to get average Parameter Values for entire output
# ----------------------------------------------------------------------------
def GetAvgParamValues(pp):
# Mostly lifted from HPSA_Update.py, by Mike Byrne.  Thanks.

#**************NOT DEBUGGED******************

    db = 0 # local debug variable
    if (db): print "Starting GetGetAvgParamValues"

    engine = win32com.client.Dispatch("DAO.DBEngine.36")
    myDB = engine.OpenDatabase(OutputDB)

##    qryUpCatchs = "SELECT PPNames.PourPoint_id, UpstreamPoints_"+Basin+".UPSTRMNM "
##    qryUpCatchs += "FROM PPNames INNER JOIN UpstreamPoints_"+Basin+" ON PPNames.out_name = UpstreamPoints_"+Basin+".DNSTRMNM "
##    qryUpCatchs += "WHERE (((PPNames.PourPoint_id)='" +Basin+ "_" + Digits + "'));"

    # SQL for parameter averages:
    qryAvgParam = "SELECT IHV_ParamData.Parameter, Avg(IHV_ParamData.A02) AS AvgOfA02 "
    qryAvgParam += "FROM IHV_ParamData "
    qryAvgParam += 'WHERE (((IHV_ParamData.Parameter)="AnnualMean")) OR (((IHV_ParamData.Parameter)="CentroidTiming")) OR (((IHV_ParamData)="LowFlow")) OR (((IHV_ParamData.Parameter)="Q2")) OR (((IHV_ParamData.Parameter)="LowVsHigh")) '
    qryAvgParam += "GROUP BY IHV_ParamData.Parameter;"

    if (db): print qryAvgParam

    rs = myDB.OpenRecordset(qryUpCatchs)
    AvgParams = []
    while not rs.EOF:
        AvgParams += [[str(rs.Fields("Parameter").Value), rs.Fields("AvgOfA02").Value]]
        rs.MoveNext()
    del rs

    return AvgParams


# ----------------------------------------------------------------------------
#   Calculate Vulnerabilities
# ----------------------------------------------------------------------------
def CalcVulner(DataArray):
    
    db = 1 # local debug variable
    if (db): print "Starting Vulnerability"

    VulnArray = zeros((DataArray.shape[2],len(Scenarios), len(Scenarios)))
        # Calculated vulnerabilities: [site, scenario1, scenario2]

    # Vulnerability will be average of normalized:
        # AnnualMean, StdDev
        # CentroidTiming, Mean
        # LowFlow, Mean
        # LowVsHigh, Mean
        # NoFlowDur, Threshold
        # IfSnowmelt, Threshold
    # Averages of those for whole study are from a run done 7/8/08 (doesn't include YUB)
    AvgParams = [['CentroidTiming', -7.43E-02], ['LowFlow',	-4.48E-02], ['LowVsHigh',0.128]]
    StdParams = [['AnnualMean',	2.20E-02]]
    Thresholds = ['NoFlowDur', 'IfSnowmelt']

    # Loop through the alterations
    for sc1 in range(len(Scenarios)):
        for sc2 in range(len(Scenarios)):
            if sc1 < sc2:
                # Loop through sites
                pp = 0
                while pp < DataArray.shape[2]:
                    Vul = 0
                    # Mean params
                    for i in range(len(AvgParams)):
                        Vul += abs(DataArray[-2, MasterParamLoop.index(AvgParams[i][0]), pp, sc1, sc2]/ AvgParams[i][1])
                    # StdDev params
                    for i in range(len(StdParams)):
                        Vul += abs(DataArray[-1, MasterParamLoop.index(StdParams[i][0]), pp, sc1, sc2] / StdParams[i][1])
                    # add in threshold elements
                    # NoFlow
                    if DataArray[-2, MasterParamLoop.index('NoFlowDur'), pp,sc1,sc1] == 0 \
                    and DataArray[-2, MasterParamLoop.index('NoFlowDur'), pp,sc2,sc2] != 0:
                        Vul += 1
                    # IfSnowmelt
                    if DataArray[-2, MasterParamLoop.index('IfSnowmelt'), pp,sc1,sc1] == 1 \
                    and DataArray[-2, MasterParamLoop.index('IfSnowmelt'), pp,sc2,sc2] != 1:
                        Vul += 1

                    VulnArray[pp,sc1,sc2] = Vul/(len(AvgParams)+len(Thresholds))
                    pp +=1

    return VulnArray

# ----------------------------------------------------------------------------
#   Duration of Base Flow
# ----------------------------------------------------------------------------
def BaseFlow(catchcsv):
# Calculate the Baseflow parameters.

    db = 1 # local debug variable
    write = 0 # to write out these sub-results to a csv file.

    if (db): print "\nStarting BaseFlow"

    # Initialize results arrays:
    BaseArray = zeros((HydData.shape[0], len(BaseflowParamLoop) ,HydData.shape[2]))
        # Baseflow results: [year, BaseFlow parameters, pourpoints]

    # Get runoff values (reported by WEAP 'catchments')
    RunArray = PointFromCatch(catchcsv) #[year,week,pourpoint]

    pp = 0
    while pp<RunArray.shape[2]:
        y = 0
        while y<(RunArray.shape[0]-1): # can't calculate for last year, because usually ends in the following year.
            if alltrue(RunArray[y,15:,pp] != 0):
                print "There are no zero runoff values for summer", 1981+y, "pour point", pp+1
                BaseArray[y,:,pp] = nan
            else:
                # calculate start of baseflow
                w = 15 # start after winter
                while w<(RunArray.shape[1]-1):
                    if RunArray[y,w,pp] == 0 and RunArray[y,w+1,pp] == 0:
                        BaseArray[y,0,pp] = w
                        break
                    w = w+1
                if BaseArray[y,0,pp] == 0:
                    print "No baseflow start week was found for wateryear:", 1981+y, " pourpoint:", pp+1
                    BaseArray[y,0,pp] = nan

                # calculate end of baseflow
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
                    while w >= BaseArray[y,0,pp] + 3:
                        if RunArray[y,w-2,pp] == 0 and RunArray[y,w-1,pp] != 0 and RunArray[y,w,pp] != 0:
                            BaseArray[y,1,pp] = (w-1)
                            break
                        w = w-1
                # and if you -still- got nothing, then it didn't work.
                if BaseArray[y,1,pp] == 0:
                    print "No baseflow end week was found for wateryear:", 1981+y, " pourpoint:", pp+1
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
        PrintName = 'BaseFlow_' + Basin + Scen + '.csv'
        print "Writing BaseArray to csv file:", PrintName, "shape:", PrintArray.shape
        savetxt(PrintName, PrintArray, delimiter = ',', fmt='%f')

    return BaseArray

# ----------------------------------------------------------------------------
#   Recession Limb Slope
# ----------------------------------------------------------------------------
def RecessionLimb(catchcsv):
# Calculate the Recession Limb Slope parameters.

    db = 0 # local debug variable
    write = 0 # to write out these sub-results to a csv file.

    if (db): print "\nStarting RecessionLimb"

    # Initialize results arrays:
    RecLimbArray = zeros((HydData.shape[0], len(RecLimbParamLoop) ,HydData.shape[2]))
        # RecessionLimb results: [year, RecessionLimb parameters, pourpoints]

    # Get Snowmelt values (reported by WEAP 'catchments')
    SnowmeltArray = PointFromCatch(catchcsv) #[year,week,pourpoint]

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
    #********************file names
    if (write):
        PrintArray = hstack(array_split(RecLimbArray,21))[0,:,:]
        PrintName = 'RecLimb_' + Basin + '_' + Scen + '.csv'
        print "Writing RecLimbArray to csv file:", PrintName, "shape:", PrintArray.shape
        savetxt(PrintName, PrintArray, delimiter = ',', fmt='%f')

    return RecLimbArray

# ----------------------------------------------------------------------------
#   Write Parameter Values to Database
# ----------------------------------------------------------------------------
def WriteParamToDB(DataArray):
    # Loops through each Wateryear/Point/Parameter combination, and writes a line to the DB table
    # with all the various parameter and alteration values

#***** Name and location of database and table should be variables up top, not just hardwired in here.

    db = 0 # local debug variable

    # connect to database
    conn = odbc.Connection(
        "Driver={Microsoft Access Driver (*.mdb)};Dbq=" + OutputDB + ";Uid=Admin;Pwd=;")
    crs = conn.cursor()

    # Columns in database, as of 7-5-08:
    ColumnList = ['Site', 'Wateryear', 'Parameter', 'T00', 'A02', 'A04', 'A06', 'T02', 'A24', 'A26', 'T04', 'A46', 'T06']

    y,p,pp = 0,0,0
    while y<DataArray.shape[0]:
        while p< DataArray.shape[1]:
            while pp< DataArray.shape[2]:

                if (db):
                    print "Generate lists"
                TableList = []
                # site:
                Digits = pp+1
                if Digits<10:
                    Digits = '0' + str(Digits)
                else:
                    Digits = str(Digits)
                TableList += [Basin+"_"+Digits]
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
                SQLString = "insert into IHV_ParameterData ("
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
#   Write Vulnerability to Database
# ----------------------------------------------------------------------------
def WriteVulnToDB(DataArray):
    # Loops through each site and writes a line to the DB table with V for each
    # scenario combination.

    db = 0 # local debug variable

    # connect to database
    conn = odbc.Connection(
        "Driver={Microsoft Access Driver (*.mdb)};Dbq=" + OutputDB + ";Uid=Admin;Pwd=;")
    crs = conn.cursor()

    # Columns in database, as of 7-5-08:
    ColumnList = ['Site', 'V02', 'V04', 'V06', 'V24', 'V26', 'V46']

    pp = 0
    while pp < DataArray.shape[0]:

        if (db):
            print "Generate list"
        TableList = []
        # site:
        Digits = pp+1
        if Digits<10:
            Digits = '0' + str(Digits)
        else:
            Digits = str(Digits)
        TableList += [Basin+"_"+Digits]
        # Vulnerability values
        sc1 = 0
        sc2 = 0
        while sc1 < len(Scenarios):
            while sc2 < len (Scenarios):
                if sc1 < sc2:
                    TableList += [DataArray[pp,sc1,sc2]]
                sc2 += 1
            sc1 += 1
            sc2 = 0

        TableTuple = tuple(TableList) # oops, execute command wants ()

        if db:
            print "TableList:", TableList
            print "ColumnList:", ColumnList

        # Generate SQL command
        SQLString = "insert into IHV_Vulnerability ("
        for col in ColumnList:
            SQLString += col + ","
        SQLString = SQLString[:-1] + ") values (" + "?,"*(len(ColumnList)-1) + "?)"
        if db: print SQLString

        # Write that line
        if db: print "Write line to database table"
        crs.execute(SQLString,TableTuple)

        pp += 1

    conn.commit()
    conn.close()

# ----------------------------------------------------------------------------
#   Main - Start program
# ----------------------------------------------------------------------------

if (debug):
    print "starting...\n"

for Basin in Basins:
    if (debug):
        print "** Basin:", Basin, '\n'
        print "Generating iteration loops:"
    QLoop = []
    RunoffLoop = []
    SnowmeltLoop = []
    for scen in Scenarios:
        QLoop += [Basin + '_PourPoints_DeltaT= ' + scen[-1] + '.csv']
        RunoffLoop += [Basin + '_SurfaceRunoff_DeltaT= ' + scen[-1] + '.csv']
        SnowmeltLoop += [Basin + '_SnowMelt_DeltaT= ' + scen[-1] + '.csv']
    #QLoop = ['MOK_PourPoints_DeltaT= 0.csv']
    #QLoop = ['MOK_PourPoints_DeltaT= 0.csv','MOK_PourPoints_DeltaT= 2.csv', 'MOK_PourPoints_DeltaT= 4.csv','MOK_PourPoints_DeltaT= 6.csv']
    #RunoffLoop = ['MOK_SurfaceRunoff_DeltaT= 0.csv']

    #****Generate ContribList list here
    #****Generate PPOrder here
        #then have the reading functions reference these lists.
        
    if (debug):
        print 'TotalQ filenames:', QLoop
        print 'Runoff filenames:', RunoffLoop
        print 'Snowmelt filenames:', SnowmeltLoop

    try:
        # loop through scenarios, generating first the QTotal-based parameters,
        #   then the catchment-reported parameters
        i = 0
        while i<len(QLoop):
            if (debug):
                print '\n', QLoop[i]
            InputArray(QLoop[i]) #loads the QTotal data into HydData array
            if (debug):
                print "InputArray run."
                print "Check: Week 42, 1984, pp1 =", HydData[4,2,0]
            # Initialize Parameters array - needs to happen after the HydData is in place, to know dimensions
            if i == 0:
                if (debug): print "Initializing Parameters array."
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

            # Baseflow parameters
            if (debug): print "Running BaseFlow."
#            Parameters[:,(len(AnnualParamLoop)+len(SumParamLoop)):(len(AnnualParamLoop)+len(SumParamLoop)+len(BaseflowParamLoop)),:,i,i] = BaseFlow(RunoffLoop[i])

            # Recession Limb Parameters
            if (debug): print "Running RecessionLimb."
#            Parameters[:,(len(AnnualParamLoop)+len(SumParamLoop)+len(BaseflowParamLoop)):,:,i,i] = RecessionLimb(SnowmeltLoop[i])
            
            if (debug):
                print "Parameter values array for T=" + str(i*2) + " generated."
                print 'Check: Mean flow past pp1 in wy1981 under this scenario =', \
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

        # write Parameter outputs.
        if (debug): print "\n", Basin, "- Writing Params and alts to database table (this may take a while)."
        WriteParamToDB(Parameters)
        if (debug): print "Written."

        # Calculate Vulnerabilities.
        if (debug): print "\n", Basin, "- Calculating Vulnerability values."
        Vulnerability = zeros((HydData.shape[2], len(BaseflowParamLoop) ,HydData.shape[2]))
            # Calculated vulnerabilities: [site, scenario1, scenario2]
        Vulnerability = CalcVulner(Parameters)

        # write Vulnerability outputs.
        if (debug): print "\n", Basin, "- Writing vulnerabilities to database table."
        WriteVulnToDB(Vulnerability)
        if (debug): print "Written."



    except:
        print sys.exc_info()[1]
        print "Darn.  Aborted."

print "end end"
        
print ""
