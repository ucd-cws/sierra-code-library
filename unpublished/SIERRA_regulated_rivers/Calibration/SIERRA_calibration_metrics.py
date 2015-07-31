from win32com.client import Dispatch
import numpy as np
from matplotlib import pyplot as plt
import csv, math
from collections import OrderedDict

resultsdir = r'C:\SIERRA\R3_results'
dbname = 'SIERRA_R3_calib.accdb'
dbpath = resultsdir+'\\'+dbname

conn = Dispatch("ADODB.Connection")
conn.Provider= "Microsoft.ACE.OLEDB.12.0"
conn.ConnectionString = "Data Source={};Persist Security Info=False;".format(dbpath)
conn.Open()

dbEpath = r'C:\SIERRA\Calibration\HistoricalEnergy.accdb'
connE = Dispatch("ADODB.Connection")
connE.Provider= "Microsoft.ACE.OLEDB.12.0"
connE.ConnectionString = "Data Source={};Persist Security Info=False;".format(dbEpath)
connE.Open()

def GetSeason(w):
    return math.ceil(w/13.)

def RemoveZeros(o, m):
    k = 0
    o = np.array(o)
    m = np.array(m)
    o_new = o.copy()
    m_new = m.copy()
    for j in range(len(o)):
        if o[j]==0 or m[j]==0:
            o_new = np.delete(o_new,j-k)
            m_new = np.delete(m_new,j-k)
            k += 1
    
    return o_new, m_new
            
def nsme(o,m):
    o, m = RemoveZeros(o, m)
            
    oMean = np.mean(o)
    result = 1-np.sum(pow((o-m),2))/np.sum(pow((o-oMean),2))
    return result

def rmse(o, m):
    
    o, m = RemoveZeros(o, m)
    
    result = math.sqrt(np.sum((o - m)**2))
    return result

def mBias(o,m):
    o, m = RemoveZeros(o, m)
    
    result = np.mean(m - o)
    return result

# HYDROPOWER TURBINE FLOWS

# all mean hydropower turbine flow values

rcparams = { \
    'xtick.major.size': 2,
    'ytick.major.size': 2,
    'xtick.labelsize' : 6,
    'ytick.labelsize' : 6,
    'axes.labelsize' : 7,
    'axes.titlesize' : 7,
    'savefig.dpi': 150}

plt.rcParams.update(rcparams)

ppQlist = OrderedDict()
for row in csv.reader(open('ppQlist.csv','rb')):
    ppQlist[row[0]] = row[1]
    
# mean weekly flow
# #################

ppObsQ = {}
ppModQ = {}

ppObsQmean = []
ppModQmean = []

# define time steps
years = range(1981,2001)
weeks = range(1,53)
seasons = range(1,5)
timesteps = [(y,w) for y in years for w in weeks]
seasonsTS = [(y,s) for y in years for s in seasons]

secsinweek = np.ones(52)*7*24*3600
secsinweek[51] = secsinweek[51]*8./7
secsinweek = np.tile(secsinweek,20)

siw = OrderedDict() # seconds in week
for i,ts in enumerate(timesteps):
    siw[ts] = secsinweek[i]
    
wis = {} # weeks in seasons
wis[1] = range(1,14)
wis[2] = range(14,27)
wis[3] = range(27,40)
wis[4] = range(40,53)

nsme_weekly = OrderedDict()
rmse_weekly = OrderedDict()
mbias_weekly = OrderedDict()

nsme_seasonal = OrderedDict()
rmse_seasonal = OrderedDict()
mbias_seasonal = OrderedDict()

nsme_annual = OrderedDict()
rmse_annual = OrderedDict()
mbias_annual = OrderedDict()

Qmean_weekly = OrderedDict()
Qmean_seasonal = OrderedDict()
Qmean_annual = OrderedDict()
    
f = open('metrics.csv','wb')
writer = csv.writer(f)

# metrics
writedata = [['Powerplant','Watershed', 'Metric type','Value']]

for p,pp in enumerate(ppQlist.keys()):
    
    ws = ppQlist[pp]
    
    mQrs = conn.Execute('SELECT WYear, WWeek, Sum(ResultValue) AS AvgOfResultValue \
    FROM [Hydropower Turbine Flow] \
    WHERE FeatureName="{}" \
    GROUP BY WYear, WWeek;'.format(pp))[0]

    relQrs = conn.Execute('SELECT WYear, WWeek, Sum(ResultValue) AS AvgOfResultValue \
    FROM [Streamflow Relative to Gauge (Absolute)] \
    WHERE FeatureName="{}" \
    GROUP BY WYear, WWeek;'.format(pp))[0]
    
    mQdata = mQrs.GetRows()
    mTS = [(mQdata[0][i], mQdata[1][i]) for i in range(len(mQdata[0]))]
        
    relQdata = relQrs.GetRows()
    relTS = [(relQdata[0][i], relQdata[1][i]) for i in range(len(relQdata[0]))]
    
    ts_match = []
    mQ = OrderedDict()
    for i,ts in enumerate([tuple(t) for t in mTS]):        
        mQ[ts] = mQdata[2][i]/siw[tuple(ts)]
            
    oQ = OrderedDict()
    for i,ts in enumerate([tuple(t) for t in relTS]):
        oQ[ts] = mQ[ts] - relQdata[2][i]/siw[tuple(ts)]    
        
    # Weekly
    # ===============================================    
    oQ_weekly = np.array(oQ.values())
    mQ_weekly = np.array(mQ.values())
    # ==============================================        
        
    # Weekly mean
    # ===============================================    
    oQ_weekly_2d = oQ_weekly.reshape(-1,52)
    mQ_weekly_2d = mQ_weekly.reshape(-1,52)

    oQ_weekly_mean = np.array([np.sum(oQ_weekly_2d[:,i])/(np.count_nonzero(oQ_weekly_2d[:,i])) \
                               for i in range(52)])
    mQ_weekly_mean = np.array([np.sum(mQ_weekly_2d[:,i])/np.count_nonzero(mQ_weekly_2d[:,i]) \
                               for i in range(52)])    
    # ==============================================
    
    
    # Seasonal
    # =========================    
    mQ_weekly_2d = mQ_weekly.reshape(-1,13)
    oQ_weekly_2d = oQ_weekly.reshape(-1,13)
    
    mQ_seasonal = np.zeros(len(years)*4)
    oQ_seasonal = mQ_seasonal.copy()
    
    for i in range(len(years)*4):
        
        mcnt = np.count_nonzero(mQ_weekly_2d[i])
        if mcnt==13:
            mQ_seasonal[i] = mQ_weekly_2d[i,:].sum()/mcnt
            
        ocnt = np.count_nonzero(oQ_weekly_2d[i])
        if ocnt==13:
            oQ_seasonal[i] = oQ_weekly_2d[i,:].sum()/ocnt    
    # =========================
    
    # Seasonal mean
    # ======================================================
    mQ_seasonal_2d = mQ_seasonal.reshape(-1,4)
    oQ_seasonal_2d = oQ_seasonal.reshape(-1,4)
    
    mQ_seasonal_mean = np.array([np.sum(mQ_seasonal_2d[:,i])/np.count_nonzero(mQ_seasonal_2d[:,i]) \
                                 for i in range(4)])
    oQ_seasonal_mean = np.array([np.sum(oQ_seasonal_2d[:,i])/np.count_nonzero(oQ_seasonal_2d[:,i]) \
                                 for i in range(4)])
    # ======================================================
    
    # Annual    
    # ==============================================
    oQ_annual = np.zeros(len(years))
    mQ_annual = oQ_annual.copy()
    
    for i in range(len(years)):
        a = i*52; b = a+52
        
        ocnt = np.count_nonzero(oQ_weekly[a:b])
        if ocnt/52. >= 0.75:
            oQ_annual[i] = np.sum(oQ_weekly[a:b])/ocnt
            
        mcnt = np.count_nonzero(mQ_weekly[a:b])
        if mcnt/52. >= 0.75:
            mQ_annual[i] = np.sum(mQ_weekly[a:b])/mcnt
    # =============================================

    # Mean
    # =============================================
    cnt = 0
    oQ_mean = 0.0
    mQ_mean = 0.0
    for i in range(len(timesteps)):
        if oQ_weekly[i]:
            cnt += 1
            oQ_mean += oQ_weekly[i]
            mQ_mean += mQ_weekly[i]
    oQ_mean /= cnt
    mQ_mean /= cnt       
    # =============================================
        
    # weekly metrics
    # ##############
    nsme_weekly[pp] = nsme(oQ_weekly, mQ_weekly)
    rmse_weekly[pp] = rmse(oQ_weekly, mQ_weekly)    
    mbias_weekly[pp] = mBias(oQ_weekly, mQ_weekly)
    
    writedata.append([pp, ws, 'Qmean_obs (cms)', oQ_mean])
    writedata.append([pp, ws, 'Qmean_mod (cms)', mQ_mean])
    writedata.append([pp, ws, 'NSME_weekly (%)', nsme_weekly[pp]])
    writedata.append([pp, ws, 'RMSE_weekly (cms)', rmse_weekly[pp]])
    writedata.append([pp, ws, 'RMSE_weekly (%)', rmse_weekly[pp] / oQ_mean])
    writedata.append([pp, ws, 'mBias (cms)', mbias_weekly[pp]])
    writedata.append([pp, ws, 'mBias (%)', mbias_weekly[pp] / oQ_mean])
    
    # seasonal metrics
    # ################
    nsme_seasonal[pp] = nsme(oQ_seasonal, mQ_seasonal)
    rmse_seasonal[pp] = rmse(oQ_seasonal, mQ_seasonal)
    mbias_seasonal[pp] = mBias(oQ_seasonal, mQ_seasonal)

    writedata.append([pp, ws, 'NSME_seasonal (%)', nsme_seasonal[pp]])
    writedata.append([pp, ws, 'RMSE_seasonal (cms)', rmse_seasonal[pp]])
    writedata.append([pp, ws, 'RMSE_seasonal (%)', rmse_seasonal[pp] / oQ_mean])
    
    # annual metrics
    # ##############
    nsme_annual[pp] = nsme(oQ_annual, mQ_annual)
    rmse_annual[pp] = rmse(oQ_annual, mQ_annual)
    
    writedata.append([pp, ws, 'NSME_annual (%)', nsme_annual[pp]])
    writedata.append([pp, ws, 'RMSE_annual (cms)', rmse_annual[pp]])
    writedata.append([pp, ws, 'RMSE_annual (%)', rmse_annual[pp] / oQ_mean])
    
    ppObsQ[pp] = oQ
    ppModQ[pp] = mQ
    
    print len(oQ.values())

# write the metrics
writer.writerows(writedata)
writer = None
f.close()

# Mean weekly and seasonal
for pp in ppQlist:           
    
    fig0 = plt.figure(figsize=(6,2),dpi=150)
    ax00 = fig0.add_subplot(111)
    ax00.plot(oQ.values())
    ax00.plot(mQ.values())
    ax00.set_xlim(0,1039)
    ax00.set_title(pp)
    
    fig1 = plt.figure(figsize=(6,3),dpi=150)
    ax10 = fig1.add_subplot(111)
    ax10.plot(oQ_weekly_mean)
    ax10.plot(mQ_weekly_mean)
    ax10.set_xlim(0,51)
    ax10.set_title(pp)
    
    fig2 = plt.figure(figsize=(6,3),dpi=150)
    ax20 = fig2.add_subplot(111)
    ax20.plot(oQ_annual_mean)
    ax20.plot(mQ_annual_mean)
    ax20.set_xlim(0,len(years))
    ax20.set_title(pp)
    
    plt.show()
    plt.close('all')
    
    
for pp in ppQlist:
    
    Qmean_weekly[pp] = np.mean(oQ)
    nsme_weekly[pp] = nsme(oQ,mQ)
    rmse_weekly[pp] = rmse(oQ,mQ)
    mbias_weekly[pp] = mBias(oQ,mQ)
    
    writer.writerows([[pp,Qmean_weekly[pp],nsme_weekly[pp],rmse_weekly[pp],]])
    
    ppObsQ[pp] = oQ
    ppModQ[pp] = mQ

writer = None

x = Qmean_weekly.values()

fig1 = plt.figure(figsize=(4,1.5),dpi=150)
ax1 = fig1.add_subplot(121)
ax1.plot([0,70],[0,0],'-',color='grey',linewidth=0.5)
ax1.plot(x,nsme_weekly.values(),'ko',markersize=3)

fig2 = plt.figure(figsize=(4,1.5),dpi=150)
ax2 = fig2.add_subplot(121)
ax2.plot([0,70],[0,0],'-',color='grey',linewidth=0.5)
ax2.plot(x,np.array(nsme_weekly.values())/np.array(x),'ko',markersize=3)
ax2.set_ylim(-2,2)

plt.show()

###writer = csv.writer(open('mean_weekly_metrics.csv','wb'))
###writer.writerows([['powerplant','mean flow (cms)','nsme','rmse','mean bias']])

###for pp in ppQlist:
    
    ###mQrs = conn.Execute('SELECT WWeek, Sum(ResultValue) AS AvgOfResultValue \
    ###FROM [Hydropower Turbine Flow] \
    ###WHERE FeatureName="{}" AND WYear < 2000 \
    ###GROUP BY WWeek;'.format(pp))[0]

    ###relQrs = conn.Execute('SELECT WWeek, Sum(ResultValue) AS AvgOfResultValue \
    ###FROM [Streamflow Relative to Gauge (Absolute)] \
    ###WHERE FeatureName="{}" AND WYear < 2000\
    ###GROUP BY WWeek;'.format(pp))[0]
    
    ###mQdata = mQrs.GetRows()
    ###mTS = list(mQdata[0])
        
    ###relQdata = relQrs.GetRows()
    ###relTS = list(relQdata[0])
    
    ###mQ = []
    ###for i,ts in enumerate(mTS):
        ###if relTS.count(ts):
            ###Q = mQdata[1][i]/7/24/3600
            ###if ts==52: Q = Q*8/7
            ###mQ.append(Q)
            
    ###relQ = []
    ###for i,ts in enumerate(relTS):
        ###if mTS.count(ts):
            ###Q = relQdata[1][i]/7/24/3600
            ###if ts==52: Q = Q*8/7
            ###relQ.append(Q)
        
    ###mQ = np.array(mQ)
    ###relQ = np.array(relQ)
    ###oQ = mQ - relQ
    
    ###writer.writerows([[pp,np.mean(oQ),nsme(oQ,mQ),rmse(oQ,mQ),mBias(oQ,mQ)]])
    
    ###ppObsQ[pp] = oQ
    ###ppModQ[pp] = mQ    
    
###writer = None    
    
connE.Close(); connE = None
conn.Close(); conn = None
    
print('finished')