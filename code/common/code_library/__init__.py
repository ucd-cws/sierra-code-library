'''
Created on Mar 3, 2012

@author: Nick
'''

import common

__all__=['common']

def isiterable(item):
	'''tests whether an object is iterable'''
	if hasattr(item,'__iter__'):
		return True
	else:
		return False