'''
Created on Mar 3, 2012

@author: Nick
'''

import arcpy

import common
from common import log
use_in_memory = True # a configuration flag that sets whether or not to use the in_memory workspace for temp files
temp_datasets = [] # a registry for temp datasets so that you can always clean up if you want to

__all__=['common']

def isiterable(item):
	'''tests whether an object is iterable'''
	if hasattr(item,'__iter__'):
		return True
	else:
		return False
	
def temp_cleanup():
	global temp_datasets
	retained = []
	for dataset in temp_datasets:
		try:
			arcpy.Delete(dataset)
		except:
			retained.append(dataset)
			log.warning("Couldn't delete all temporary datasets")
	temp_datasets = retained