import sys

from code_library.common.image import remote_cam

try:
	folder = sys.argv[1]
except IndexError:
	folder = None

try:
	output_csv = sys.argv[2]
except IndexError:
	output_csv = None

if not folder:
	folder = raw_input("Please enter the full path of folder to read\n")
if not output_csv:
	output_csv = raw_input("Please enter the full path of the output csv\n")

print "Writing File"
remote_cam.baropressures_to_file(folder, output_csv)

raw_input("Done. Press any key to exit")