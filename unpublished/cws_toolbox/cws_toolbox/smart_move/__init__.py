__author__ = 'nrsantos'

import os

import arcpy



__all__ = ["common","smart_move_features"]

# have a "smart move folder," "smart move geodatabase," "smart move raster," and "smart move feature class." Same underlying code, different move operations
# get the from and to locations
# advanced options for portion of from to match and ways to reference the to. For version 1, it'll be 1:1. Version 2 we can match the from, and version three will allow us to set up how the to is done.

