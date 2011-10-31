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
    'xtick.major.size': 0,
    'ytick.major.size': 1,
    'xtick.labelsize' : 5,
    'ytick.labelsize' : 5,
    'axes.labelsize' : 6,
    'axes.titlesize' : 7,
    'savefig.dpi': 600,
    'axes.color_cycle': ['#FFC000','#FF8000','#FF4000','#FF0000']}

plt.rcParams.update(rcparams)

#w = [date(1980,10,1)+timedelta(days=7*i) for i in range(13)]+[date(1981,1,1)+timedelta(days=7*i) for i in range(39)]
w = mdates.drange(date(1980,10,1),date(1980,12,30),timedelta(days=7))
w = np.append(w,mdates.drange(date(1981,1,1),date(1981,9,30),timedelta(days=7)))

# total weekly generation by dT

basins = ['FEA','ABY','MOK','STN','TUO','SJN','KNG','KAW','TUL','KRN']
colors = ['#FFC000','#FF8000','#FF4000','#FF0000']
xmin = -0.2
xmax = 4.2
lw = 0.5

fig = plt.figure(figsize=(6,3),dpi=150)
for i,basin in enumerate(basins):
    n = float(len(basins))
    l = i/(n+1.2)+0.09
    w = 1/(n+1.2)
    ax0 = fig.add_axes((l,0.65,w,0.22))
    ax1 = fig.add_axes((l,0.4,w,0.22))
    ax2 = fig.add_axes((l,0.15,w,0.22))
    
    sql = "SELECT GCM, Sum(ResultValue)/20/3600 \
    FROM [Hydropower Generation] \
    WHERE Basin='{}'\
    GROUP BY GCM;".format(basin)
    rs = conn.Execute(sql)[0]
    E = np.array(rs.GetRows()[1])
    
    x0 = np.copy(E)
    ax0.bar(np.arange(4)+0.1,x0,color=colors,linewidth=lw)
    ax0.set_title(basin)
    ax0.set_ylim(0,6000)
    ax0.set_xticklabels([])
    ax0.set_xlim(xmin,xmax)
    
    x1 = (E-E[0])
    ax1.bar(np.arange(4)+0.1,x1,color=colors,linewidth=lw)
    ax1.set_ylim(-1200,200)
    ax1.set_xticklabels([])
    ax1.set_xlim(xmin,xmax)
    
    x2 = (E/E[0]-1)*100
    ax2.bar(np.arange(4)+0.1,x2,color=colors,linewidth=lw)
    ax2.set_ylim(-20,5)
    #xlabels=['+{}$ ^\circ$'.format(T) for T in range(0,7,2)]
    ax2.set_xticklabels(['{}$^\circ$'.format(t) for t in [0,2,4,6]])
    ax2.set_xlim(xmin,xmax)
    
    if i==0:
        ax0.set_ylabel('Energy\n(GWh/year)',ha='center',labelpad=8)
        ax1.set_ylabel('$\Delta$ Energy\n(GWh/year)',ha='center',labelpad=8)
        ax2.set_ylabel('$\Delta$ Energy\n(%)',ha='center',labelpad=8)
    else:
        ax0.set_yticklabels([])
        ax1.set_yticklabels([])
        ax2.set_yticklabels([])
    for ax in [ax0,ax1,ax2]:
        ax.set_xticks(np.arange(1,5)-0.5)

fig.text(0.5,0.06,'Temperature increase (degrees Celsius)',ha='center',size=7)
plt.savefig('Energy change by basin.png')
plt.show()
conn.Close()
conn = None