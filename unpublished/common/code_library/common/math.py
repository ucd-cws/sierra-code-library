'''
Created on Mar 3, 2012

@author: Nick
'''

class min_max():
	def __init__(self, tmin = 0, tmax = 0):
		self.min = tmin
		self.max = tmax
		self.n = 0

	def track(self,item):
		
		item = self.mm_coerce(item)

		if item < self.min:
			self.min = item
		elif item > self.max:
			self.max = item
			
		self.n += 1
	
	def report(self, return_text = False):
		self_report = "Min: %s, Max: %s, n: %s" % (self.min,self.max,self.n)
		
		if return_text:
			return self_report
		else:
			print self_report
	
	def stretch(self,s_value,low = 0,high = 1):
		s_value = self.mm_coerce(s_value)

		new_val = (( (float(s_value) - float(self.min))/(float(self.max) - float(self.min))) * (float(high)-float(low)) + float(low)) # conduct adjustment
			
		return new_val
	
	def mm_coerce(self,item):
		
		if type(item) != "int" and type(item) != "float":
			try:
				item = int(item) # coerce it into into
			except:
				try:
					item = float(item)
				except:
					raise TypeError("Couldn't coerce '%s' into int or float - we're not going to order a string for you!" % item)
		
		return item
