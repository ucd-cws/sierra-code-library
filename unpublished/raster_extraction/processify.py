import os
import sys
import traceback
from functools import wraps
from multiprocessing import Process, Queue

#import config

'''
Retrieved from https://gist.github.com/2311116 via http://stackoverflow.com/questions/2046603/is-it-possible-to-run-function-in-a-subprocess-without-threading-or-writing-a-se

Modified by Nick Santos to allow for conditional returning of the function based on preferences

'''

def processify(func):
	'''Decorator to run a function as a process.

	Be sure that every argument and the return value
	is *pickable*.

	The created process is joined, so the code does not
	run in parallel.

	'''
	#if not config.use_subprocesses: # if we don't want to use subprocesses, then just return the arg
	#	return func
	
	# register original function with different name
	# in sys.modules so it is pickable
	def process_func(q, *args, **kwargs):
		try:
			ret = func(*args, **kwargs)
		except Exception:
			except_type, except_class, tb = sys.exc_info()
			q.put((except_type, except_class, traceback.format_tb(tb)))
		else:
			q.put(ret)

	process_func.__name__ = func.__name__ + 'processify_func'
	setattr(sys.modules[__name__], process_func.__name__, process_func)

	@wraps(func)
	def wrapper(*args, **kwargs):
		q = Queue()
		p = Process(target=process_func, args=[q] + list(args), kwargs=kwargs)
		p.start()
		ret = q.get()
		p.join()
		error = None
		try:
			if len(ret) == 3 and issubclass(ret[0], Exception):
				msg = '%s\n' % ret[1]
				org_traceback = ''.join(line for line in ret[2])
				error = ret[0](msg + org_traceback)
		except TypeError:
			pass
		else:
			if error:
				raise error
		return ret
	return wrapper



@processify
def test_function():
	return os.getpid()


@processify
def test_exception():
	print os.getpid()
	raise RuntimeError()


def test():
	print os.getpid()
	print test_function()
	#test_exception()
