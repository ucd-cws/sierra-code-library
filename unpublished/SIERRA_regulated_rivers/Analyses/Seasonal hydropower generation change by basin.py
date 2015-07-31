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
    'axes.color_cycle': ['#FFC000','#FF8000','#FF4000','#FF0000']}

plt.rcParams.update(rcparams)

c = ['#FFC000','#FF8000','#FF4000','#FF0000']

#w = [date(1980,10,1)+timedelta(days=7*i) for i in range(13)]+[date(1981,1,1)+timedelta(days=7*i) for i in range(39)]
#wk = mdates.drange(date(1980,10,1),date(1980,12,30),timedelta(days=7))
#wk = np.append(wk,mdates.drange(date(1981,1,1),date(1981,9,30),timedelta(days=7)))
seasondefs = [(0,13),(13,26),(26,40),(40,52)]
# total weekly generation by dT

basins = ['FEA','ABY','MOK','STN','TUO','SJN','KNG','KAW','TUL','KRN']

ms = 3
lw = 0.5
fig = plt.figure(figsize=(6,3.5),dpi=150)
lines = []
for i,basin in enumerate(basins):
    n = float(len(basins))
    l = i/(n+1.2)+0.09
    w = 1/(n+1.2)
    ax0 = fig.add_axes((l,0.65,w,0.2))
    ax1 = fig.add_axes((l,0.4,w,0.2))
    ax2 = fig.add_axes((l,0.15,w,0.2))
    
    sql = "SELECT GCM, WWeek, Sum(ResultValue)/20/3600 \
    FROM [Hydropower Generation] \
    WHERE Basin='{}'\
    GROUP BY GCM, WWeek;".format(basin)
    rs = conn.Execute(sql)[0]
    data = np.array(rs.GetRows()[2])
    
    E = data.reshape((4,-1))
    
    # plot each seasonal graph; j = warming scenario
    for j in range(0,4):
        x0 = E[j]
        xzero = np.array([np.sum(E[0][a:b]) for (a,b) in seasondefs])
        xabs = np.array([np.sum(x0[a:b]) for (a,b) in seasondefs])
        xdel = xabs - xzero
        xrel = (xabs/xzero - 1)*100

        xabsplt = np.hstack((xabs[-1],xabs,xabs[0]))
        xdelplt = np.hstack((xdel[-1],xdel,xdel[0]))
        xrelplt = np.hstack((xrel[-1],xrel,xrel[0]))
        
        l = ax0.plot(xabsplt,'o-',markersize=ms,linewidth=lw, color = c[j], markerfacecolor=c[j])
        if i==0:
            lines.append(l)
        if j:
            msp = ms
        else:
            msp = 0
        ax1.plot(xdelplt,'o-',markersize=msp,linewidth=lw, color = c[j], markerfacecolor=c[j])
        ax2.plot(xrelplt,'o-',markersize=msp,linewidth=lw, color = c[j], markerfacecolor=c[j])
        if j==0:
            ax1.plot(np.zeros(6),'k')
            ax2.plot(np.zeros(6),'k')
        
        for ax in [ax0,ax1,ax2]:
            ax.set_xlim(0.5,4.5)
            ax.set_xticks(range(1,5))
            ax.set_xticklabels(['O','J','A','J'])

    ax0.set_ylim(0,2500)
    #ax0.set_xticklabels([])     
    ax0.set_title(basin)
    
    ax1.set_ylim(-800,800)
    #ax1.set_xticklabels([])
    
    ax2.set_ylim(-100,100)
    #ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
    #ax1.set_xlim(date(1980,10,1),date(1981,9,24))
    #ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
    #ax2.xaxis.set_major_formatter(mdates.DateFormatter('01-%b'))
    #ax2.set_xlim(date(1980,10,1),date(1981,9,24))
    
    if i==0:
        ax0.set_ylabel('Energy\n(GWh/season)',ha='center',labelpad=9)
        ax1.set_ylabel('$\Delta$ Energy\n(GWh/season)',ha='center',labelpad=9)
        ax2.set_ylabel('$\Delta$ Energy\n(%)',ha='center',labelpad=9)
    else:
        ax0.set_yticklabels([])
        ax1.set_yticklabels([])
        ax2.set_yticklabels([])
fig.legend(lines, [r'+{}$^\circ$C'.format(T) for T in [0,2,4,6]], loc=(0.615,0.79), prop={'size':5}, ncol=4)
fig.text(0.5,0.08,'Season (O = OND, J = JFM, A = AMJ, J = JAS)',ha='center',size=7)
plt.savefig('Seasonal energy change by basin.png')
plt.show()