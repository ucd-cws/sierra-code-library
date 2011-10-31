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
    'xtick.labelsize' : 6,
    'ytick.labelsize' : 6,
    'axes.labelsize' : 7,
    'axes.titlesize' : 8,
    'savefig.dpi': 600}

plt.rcParams.update(rcparams)

#w = [date(1980,10,1)+timedelta(days=7*i) for i in range(13)]+[date(1981,1,1)+timedelta(days=7*i) for i in range(39)]
w = mdates.drange(date(1980,10,1),date(1980,12,30),timedelta(days=7))
w = np.append(w,mdates.drange(date(1981,1,1),date(1981,9,30),timedelta(days=7)))

# total weekly generation by dT

sql = 'SELECT GCM, WWeek, Sum(ResultValue)/19/3600 \
FROM [Hydropower Generation] \
WHERE WYear<2000 \
GROUP BY GCM, WWeek;'
rs = conn.Execute(sql)[0]
data = np.array(rs.GetRows()[2])
data = data.reshape((4,-1))

fig = plt.figure(figsize=(6,5),dpi=150)
fig.subplots_adjust(hspace=0.4)
ax0 = fig.add_subplot(311)
ax1 = fig.add_subplot(312)
ax2 = fig.add_subplot(313)
sym = {0:'s',1:'o',2:'^',3:'v'}
colors = ['#FFC000','#FF8000','#FF4000','#FF0000']
i=-1
lines = []
for j,ax in enumerate([ax0,ax1,ax2]):
    ax.plot([date(1980,10,1),date(1981,9,24)],[0,0],color='k',linewidth=0.5)
for E in data[0:]:
    i+=1
    y0 = E
    y1 = (E - data[0])
    y2 = (E/data[0]-1)*100
    y = {0:y0,1:y1,2:y2}
    for j,ax in enumerate([ax0,ax1,ax2]):
        if i==0 and j>0:
            lw=0.5
            symbol='.'
            ms = 0
            c = 'k'
        else:
            lw=1.5
            symbol=sym[i]            
            ms = 3
            c=colors[i]
        l = ax.plot(w,y[j],linewidth=lw,marker=symbol,markersize=ms,color=c)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        if j==0:
            lines.append(l)
            
ax0.set_ylabel('Total energy (GWh/week)')
ax0.set_title(r'a) Total weekly generation')
ax1.set_ylabel('Energy change (GWh/week)')
ax1.set_title(r'b) Absolute change in weekly generation')
ax2.set_ylabel('Energy change (%/week)')
ax2.set_xlabel('Time of year')
ax2.set_title(r'c) Relative change in weekly generation')
fig.legend(lines,('+{}$^\circ$C'.format(dt) for dt in [0,2,4,6]),loc=(0.48,0.7),prop={'size':6},ncol=4)
plt.savefig('change in weekly hydropower generation.png')
plt.show()
