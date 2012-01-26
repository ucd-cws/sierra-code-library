import re

license_file = r'D:\Program Files\ArcGIS\License10.0\bin\lmgrd9.log'
cont_flag = 'y'

while cont_flag == 'y':
        l_file = open(license_file)

        user_hash = {}
        for line in l_file:
                match = re.search('OUT\: \"ARC\/INFO\" (.*)\s*$',line)
                if match is not None and match.group(1) is not None:
                        user_hash[match.group(1)] = True
                
                match_new = re.search('IN\: \"ARC\/INFO\" (.*)\s*$',line)
                if match_new is not None and match_new.group(1) is not None:
                        user_hash[match_new.group(1)] = False 

        l_file.close()

        print "Users with an ArcInfo License\n------------------------------\n"
        for key in user_hash.keys():
                if user_hash[key] is True:
                        print key

        print "\n\nCheck again? (y/n): "
        cont_flag = raw_input()
        print "\n\n------------------------------"
