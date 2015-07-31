library("raster")

setwd("E:\\Freshwater_Conservation\\Herps_Data\\Default_rasters")
rasters = list.files(path = ".", pattern = NULL, all.files = FALSE,
                     full.names = TRUE, recursive = FALSE,
                     ignore.case = FALSE, include.dirs = FALSE)

convert_raster <- function(raster_path){
  print(raster_path)
  if(grepl("grd$", raster_path)){
    t_ras = raster(raster_path)
    out_name =  paste(raster_path, ".tif", sep='')
    print(out_name)
    writeRaster(t_ras, out_name, format="GTiff")
    return(out_name)
  }else{
    return(raster_path)
  }
  
}

lapply(rasters, convert_raster)


