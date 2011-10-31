from win32com.client import Dispatch
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from datetime import date,timedelta
from collections import OrderedDict

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
    'xtick.labelsize' : 6,
    'ytick.labelsize' : 6,
    'axes.labelsize' : 6,
    'axes.titlesize' : 8,
    'savefig.dpi': 600,
    'axes.color_cycle': ['#FFC000','#FF8000','#FF4000','#FF0000']}

plt.rcParams.update(rcparams)

#w = [date(1980,10,1)+timedelta(days=7*i) for i in range(13)]+[date(1981,1,1)+timedelta(days=7*i) for i in range(39)]
w = mdates.drange(date(1980,10,1),date(1980,12,30),timedelta(days=7))
w = np.append(w,mdates.drange(date(1981,1,1),date(1981,9,30),timedelta(days=7)))

# total seasonal/annual generation by dT

seasons = OrderedDict()
seasons['OND'] = [1,13]
seasons['JFM'] = [14,26]
seasons['AMJ'] = [27,39]
seasons['JAS'] = [40,52]
seasons['Annual'] = [1,52]

fig = plt.figure(figsize=(6,3),dpi=150)
for i,season in enumerate(seasons.keys()):
    n = float(len(seasons.keys()))
    l = i/(n+1.3)+0.11
    if i==4:
        l+=0.07
    w = 1/(n+1.8)

    # add the subplots (axes)
    
    ax0 = fig.add_axes((l,0.66,w,0.25))
    ax1 = fig.add_axes((l,0.39,w,0.25))
    ax2 = fig.add_axes((l,0.12,w,0.25))
    
    sql = "SELECT GCM, WYear, Sum(ResultValue)/3600 \
    FROM [Hydropower Generation] \
    WHERE WYear<2000 AND WWeek >= {} AND WWeek <= {}\
    GROUP BY GCM, WYear;".format(seasons[season][0],seasons[season][1])
    rs = conn.Execute(sql)[0]
    data = np.array(rs.GetRows()[2])
    
    E = data.reshape((4,-1)).mean(axis=1)

    xlabels=['+{}$ ^\circ$'.format(T) for T in range(0,7,2)]    
    
    colors = ['#FFC000','#FF8000','#FF4000','#FF0000']
    
    x0 = E
    ax0.bar(np.arange(4)+0.1,x0,color=colors)
    ax0.set_title(season)
    
    x1 = (E-E[0])
    ax1.bar(np.arange(4)+0.1,x1,color=colors)
    if i<5:
        ax1.set_ylim(-2500,2500)
    
    x2 = (E/E[0]-1)*100
    ax2.bar(np.arange(4)+0.1,x2,color=colors)
    ax2.set_ylim(-35,35)

    for j,ax in enumerate([ax0,ax1,ax2]):
        ax.set_xticks(np.arange(4)+0.5)
        if j==2:
            ax.set_xticklabels(xlabels)
        else:
            ax.set_xticklabels([])
        ax.set_xlim(0.0,4.0)
    
    if i==0:
        ax0.set_ylabel('Energy (GWh)',ha='center',labelpad=9)
        ax1.set_ylabel('$\Delta$ Energy\n(GWh)',ha='center',labelpad=9)
        ax2.set_ylabel('$\Delta$ Energy\n(%)',ha='center',labelpad=9)
    elif i<=3:
        ax0.set_yticklabels([])
        ax1.set_yticklabels([])
        ax2.set_yticklabels([])
        
fig.text(0.5,0.04,'Temperature increase (degrees Celsius)',ha='center',size=7)
plt.savefig('Energy change.png')
plt.show()