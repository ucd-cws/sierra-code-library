import arcpy

from code_library.common.geospatial import geometry
from code_library.common import log

log.init_log(arc_script = True)

p1 = arcpy.GetParameterAsText(0)
p2 = arcpy.GetParameterAsText(1)

cen_dist,out_table,out_points = geometry.simple_centroid_distance(p1,p2,spatial_reference = p1,dissolve=True,return_file=True)


log.warning("Centroid Distance: %s" % cen_dist)
log.warning("Points representing the centroids and a table with the distances have been returned to the TOC")

arcpy.SetParameterAsText(2,out_points)
arcpy.SetParameterAsText(3,out_table)