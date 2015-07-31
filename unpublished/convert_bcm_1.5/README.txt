This script takes all .asc files in the input folder  and converts them to rasters in CA Teale Albers format. It will attempt to define the projection of the raster first,
so you need to do some work to know what the projection of the asc files should be and put that into the code appropriately to define it.

It will then convert and reproject the files and the finished data will be in converted.gdb