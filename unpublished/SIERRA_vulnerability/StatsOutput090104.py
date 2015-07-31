# ---------------------------------------------------------------------------
#
# Summary : Access IHV_Metrics DB and output all the means and StdDev values
#           into a single csv file, for easy data analysis.
#
# Author  : Alexandra Geddes
# Version : Jan 04, 2009
#
# Notes   : 
#
# ---------------------------------------------------------------------------

# Import system modules
import sys
import win32com.client

# Script Debugging
debug = 0

# Outside data structure
drive_letter = 'C:'
IHV_dir = "C:\Documents and Settings\Alex\My Documents\PhysicalHabitatMetrics\Python\IHV_Bundle"
OutputDB = IHV_dir + '\\IHV_Output\IHV_Output.mdb'
StatsFileName = IHV_dir + '\\IHV_Output\IHV_stats.csv'

# Loop Arrays
AnnualParamLoop = ['AnnualMean', 'QAnnual', 'CentroidTiming', 'LowFlow', 'HighFlow', 'WeekHighFlow', \
'LowVsHigh', 'NoFlowDur']
SumParamLoop = ['DroughtResistance', 'Q2', 'NumDryYears']
DrySeasonParamLoop = ['DrySeasonStart','DrySeasonEnd','DrySeasonDur', 'DrySeasonQAvg']
RecLimbParamLoop = ['IfSnowmelt', 'SnowmeltStart', 'SnowmeltEnd', 'SnowmeltPeakQ', \
'SnowmeltPeakDate', 'RecLimbSlope']
MasterParamLoop = AnnualParamLoop + SumParamLoop + DrySeasonParamLoop + RecLimbParamLoop
Scenarios = ['T0', 'T2', 'T4', 'T6']
# Alterations = ["T00"]
Alterations = ["T00", "A02", "A04", "A06"]
#Alterations = ["T00", "A02", "A04", "A06", "A24", "A26", "A46"]

# ----------------------------------------------------------------------------
#   Ping the IHV_Metrics database to get global-average alteration values
# ----------------------------------------------------------------------------
def GetAvgAlts(Metric, Stat):
    # Returns a list of global averages of alteration values for metrics in VulnMetrics.
    
    #***************** Not Debugged *******************

    db = 0 # local debug variable
    if (db): print "Starting GetAvgAlts"

    engine = win32com.client.Dispatch("DAO.DBEngine.36")
    myDB = engine.OpenDatabase(OutputDB)

    qryAvgs = "SELECT IHV_Metrics.A02 FROM IHV_Metrics "
    qryAvgs += 'WHERE (((IHV_Metrics.Wateryear)="' + Stat
    qryAvgs += '") AND ((IHV_Metrics.Metric)="' + Metric + '"));'

    MetricStat = 0.0
    rs = myDB.OpenRecordset(qryAvgs)
    TotalAlt = 0.0
    NumRecords = 0
    while not rs.EOF:
        try:
            float(str(rs.Fields("A02").Value))
            TotalAlt += float(rs.Fields("A02").Value)
            NumRecords += 1
        except:
            pass
        rs.MoveNext()
    del rs
    MetricStat = [TotalAlt/NumRecords]
        
    return MetricStat

# ----------------------------------------------------------------------------
#   Ping the IHV_Metrics database to get list of lists of alteration values
# ----------------------------------------------------------------------------
def GetMetricAlts(MetricName, StatType):
    # Returns a list of lists of alteration values.
    # MetricList[Location,Scenario]
    # NB: MetricList[Locations][0] - SiteID (e.g. MOK_11)
    # NB: all strings

    db = 0 # local debug variable
    if (db): print "Starting GetMetricAlts,", MetricName, StatType

    engine = win32com.client.Dispatch("DAO.DBEngine.36")
    myDB = engine.OpenDatabase(OutputDB)

    qryMetrics = "SELECT IHV_Metrics.Site"
    for Alt in Alterations:
        qryMetrics += ", IHV_Metrics." + Alt
    qryMetrics += " FROM IHV_Metrics "
    qryMetrics += 'WHERE (((IHV_Metrics.Metric)="' + MetricName + '") AND '
    qryMetrics += '((IHV_Metrics.Wateryear)="' + StatType + '")) ORDER BY IHV_Metrics.Site;'

    rs = myDB.OpenRecordset(qryMetrics)
    MetricList = []
    while not rs.EOF:
        AltList = [str(rs.Fields('Site').Value)]
        for Alt in Alterations:
            AltList += [str(rs.Fields(Alt).Value)]
        MetricList += [AltList]
        rs.MoveNext()
    del rs
    return MetricList


# ----------------------------------------------------------------------------
#   Write out values to a csv
# ----------------------------------------------------------------------------
def WriteToCSV(ValueList, StatName):
# ValueList[metric, location, scenario]
# This will be done for Mean and StdDev seperately - producing?

    db = 0 # local debug variable
    if (db): print "Starting WriteToCSV"
    
    WriteTo = open(StatsFileName, 'a')

    # List of headings
        # site, Metric_Sc, ....
    HeadersList = []
    HeadersList = ['Site']
    m = 0
    while m < len(MasterParamLoop):
        Alt = 0
        while Alt < len(Alterations):
            HeadersList += [MasterParamLoop[m] + '_' + StatName + '_' + Alterations[Alt]]
            Alt += 1
        m += 1
    HeaderStr = ''
    for x in HeadersList:
        HeaderStr += x + ','
    HeaderStr = HeaderStr[:-1] + '\n'
    # Write headers
    WriteTo.write(HeaderStr)
    
    # Each site's line
    try:
        loc = 0
        while loc < len(ValueList[0]):
            SiteList = [ValueList[0][loc][0]] # Site name
            m = 0
            while m < len(MasterParamLoop):
                Alt = 1 # Alt[0] is the Site
                while Alt < len(Alterations)+1:
                    if (db): print 'loc:', loc, "m:", m, "Alt:", Alt
                    SiteList += [ValueList[m][loc][Alt]]
                    Alt += 1
                m += 1
            SiteStr = ''
            for x in SiteList:
                SiteStr += x + ','
            SiteStr = SiteStr[:-1] + '\n'
            # Write line
            WriteTo.write(SiteStr)
            loc += 1
    except:
        print sys.exc_info()[1]
        print "Darn.  Aborted."


    WriteTo.close()

# ----------------------------------------------------------------------------
#   Main - Start program
# ----------------------------------------------------------------------------

print "starting...\n"
try:
    #Ping IHV database for global avg values in A02 for the Metrics used
#    AvgAltValues = GetAvgAlts()

    # Ping IHV database for metric/alteration values, insert into ValueList
    MeansValueList = []
    StdsValueList = []
    for MetricName in MasterParamLoop:
        # Get Alteration values
        MeansValueList += [GetMetricAlts(MetricName, 'Mean')] #returns list[scenarios]
        StdsValueList += [GetMetricAlts(MetricName, 'StdDev')] #returns list[scenarios]
        # list of lists - ValueList[metric, location, scenario]
        # NB: they are all STRINGS!  This is to accomidate some not-a-number returns
    WriteToCSV(MeansValueList, 'Mean')
    WriteToCSV(StdsValueList, 'StdDev')

except:
    print sys.exc_info()[1]
    print "Darn.  Aborted."
    
print "end end"
