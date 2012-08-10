import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from matplotlib import mlab
import datetime as dt
import os

sites = ['TUO']
site_suffix = "stage_data" # filenames are of the form (site)_(site_suffix).csv without parens. eg TUO_stage_data.csv if "TUO" is site and "stage_data" is site_suffix

#sites = ['NFA','MFA','RUB','NFY','MFY','SFY']
title = {}
title['NFA'] = 'North Fork American'
title['SFY'] = 'South Fork Yuba'
title['TUO'] = "Tuolumne"
title['CLA'] = "Clavey"

# colors are web colors...
maincolor = '#33FFFF'
futurecolor = '#505050'
pastcolor = 'cyan'
presentcolor = 'black' # color of the dot
figtransparency = True

# set up the chart colors, etc, here:
rcparams = { \
    'text.color': maincolor,
    'xtick.major.size': 0,
    'ytick.major.size': 0,
    'xtick.labelsize' : 5,
    'ytick.labelsize' : 5,
    'axes.labelsize' : 7,
    'axes.titlesize' : 9,
    'axes.labelcolor': maincolor,
    'axes.edgecolor' : maincolor,
    'xtick.color': maincolor,
    'ytick.color': maincolor,
    'grid.color' : maincolor,
    'savefig.dpi': 150}

plt.rcParams.update(rcparams)

def convert_bad_date(date):
    convert_month = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06","Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
    # format is ddmmmyyyy hhmm where mmm is the three letter month abbrev

    import re
    
    s = re.search("(\d{2})([a-zA-Z]{3})(\d{4})\s+(\d{2})(\d{2})", date)
    try:
        #print "[%s]" % s.group(5)
        good_date = "%s-%s-%s %s%s" % (convert_month[s.group(2)],s.group(1),s.group(3),s.group(4),s.group(5))
    except:
	    print "Bad date - filling with 0 date so it doesn't crash in next step"
	    good_date = "01/01/1901 00:00"
    
    return good_date

for site in sites:
    fname = '%s_%s.csv' % (site,site_suffix)
    
    data = mlab.csv2rec(fname, delimiter=',', skiprows=1)
    dates = data.date
    flows = data.cfs
    
    fake_dates = []
    i = 0
    while i < len(dates):
        fake_dates.append(i)
        i = i + 1
	
	# no need to convert dates this time
	
    #print "Converting dates"
    #for inc in range(len(dates)): # convert all the poorly formatted dates into something this will understand
    #    dates[inc] = convert_bad_date(dates[inc])
    #print "Dates converted"
	
    for i,d in enumerate(data.date):
        
        # create the figure
        fig = plt.figure(figsize=(5,3),dpi=150) # these kwargs are for display only; see 'savefig' below
        
        ax = fig.add_subplot(111,alpha=0.0)
        
        # set up the data
        x = fake_dates[:i+1]
        y = flows[:i+1]
        
        # plot the data
        ax.plot(fake_dates,flows,'-',linewidth=2,color=futurecolor) # future
        ax.plot(x,y,'-',linewidth=3,color=pastcolor) # past
        ax.plot(x[-1],y[-1],'o',color=presentcolor) # present (dot)
        
        # set up the chart
        xmin = fake_dates[0]
        xmax = fake_dates[-1]
        #datemin = dt.date(r.date.min().year, 1, 1)
        #datemax = dt.date(r.date.max().year+1, 1, 1)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(0,np.max(flows)*1.1)
        ax.set_ylabel('Discharge (cfs)')
        #ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%Y %h:%m'))
        #ax.set_title(title[site])
        
        ax.grid()
        
        # save the figure
        figname = '%s_%s.png' % (fname, d)
        
        # save the figure; set transparency
        plt.savefig(os.path.join(os.getcwd(),'figures',figname), transparent=figtransparency)
        #plt.show()
        plt.close('all')
        
print 'finished'
