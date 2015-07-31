from win32com.client import Dispatch
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from datetime import date,timedelta

resultsdir = r'C:\SIERRA\R3_results'
dbname = 'SIERRA_R3_scenarios.accdb'
dbpath = resultsdir+'\\'+dbname

conn = Dispatch("ADODB.Connection")
conn.Provider= "Microsoft.ACE.OLEDB.12.0"
conn.ConnectionString = "Data Source={};Persist Security Info=False;".format(dbpath)
conn.Open()

rcparams = { \
    'xtick.major.size': 2,
    'ytick.major.size': 2,
    'xtick.labelsize' : 5,
    'ytick.labelsize' : 6,
    'axes.labelsize' : 6,
    'axes.titlesize' : 7,
    'savefig.dpi': 600,
    'axes.color_cycle': ['#FF0000','#FF4000','#FF8000','#FFC000']}

plt.rcParams.update(rcparams)

#w = [date(1980,10,1)+timedelta(days=7*i) for i in range(13)]+[date(1981,1,1)+timedelta(days=7*i) for i in range(39)]
wk = mdates.drange(date(1980,10,1),date(1980,12,30),timedelta(days=7))
wk = np.append(wk,mdates.drange(date(1981,1,1),date(1981,9,30),timedelta(days=7)))

# total weekly generation by dT

basins = ['FEA','ABY','MOK','STN','TUO','SJN','KNG','KAW','TUL','KRN']

fig = plt.figure(figsize=(6,2.2),dpi=150)
for i,basin in enumerate(basins):
    n = float(len(basins))
    l = i/(n+1.2)+0.09
    w = 1/(n+1.2)
    ax1 = fig.add_axes((l,0.53,w,0.35))
    ax2 = fig.add_axes((l,0.16,w,0.35))
    
    sql = "SELECT GCM, WWeek, Sum(ResultValue)/19/3600 \
    FROM [Hydropower Generation] \
    WHERE WYear<2000 AND Basin='{}'\
    GROUP BY GCM, WWeek;".format(basin)
    rs = conn.Execute(sql)[0]
    data = np.array(rs.GetRows()[2])
    
    E = data.reshape((4,-1))
    for j in range(0,4):
        x1 = (E[j]-E[0])
        ax1.plot(wk,x1)
        x2 = (E[j]/E[0]-1)*100
        ax2.plot(wk,x2)
        if j==0:
            ax1.plot(wk,np.zeros(52),'k')
            ax2.plot(wk,np.zeros(52),'k')
    ax1.set_title(basin)
    ax1.set_ylim(-79,79)
    ax1.set_xticklabels([])
    
    ax2.set_ylim(-100,120)
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
    ax1.set_xlim(date(1980,10,1),date(1981,9,24))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('01-%b'))
    ax2.set_xlim(date(1980,10,1),date(1981,9,24))
    
    if i==0:
        ax1.set_ylabel('$\Delta$ Energy\n(GWh/year)',ha='center',labelpad=9)
        ax2.set_ylabel('$\Delta$ Energy\n(%)',ha='center',labelpad=9)
    else:
        ax1.set_yticklabels([])
        ax2.set_yticklabels([])
fig.text(0.5,0.04,'Time of year',ha='center',size=7)
plt.savefig('Weekly energy change by basin.png')
plt.show()