__author__ = 'Nick Santos'

import os
import sys
import traceback

home_folder = r"E:\Home"
username = raw_input("Please enter the user's SIERRA domain user name: ")

home_prompt = raw_input("Is home folder %s? (y/n)" % home_folder)
if home_prompt.lower() == "n" or home_prompt.lower() == "no":
	home_folder = raw_input("Please enter the home folder location (with no trailing slash - eg E:\Home ):")
	print "using '%s' for home folder" % home_folder

print "Making folders"


def make_folder(path, english_name):
	"""
		Makes the folder - used to wrap the exception and not repeat it.
	:param path: the path to make
	:param english_name: the name to use in the error
	:return: None
	"""
	try:
		os.mkdir(path)
	except:
		traceback.print_exc()
		print "Unable to make %s, exiting - may be incomplete folder structure in home folder" % english_name
		sys.exit()

user_folder = os.path.join(home_folder, username)
make_folder(user_folder, "base user folder")
make_folder(os.path.join(user_folder, "Private"), "user private folder")
make_folder(os.path.join(user_folder, "Public"), "user public folder")

print "Folders made - make sure to go set the appropriate permissions"


