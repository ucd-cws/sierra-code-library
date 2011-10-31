import arcpy, os, time, string
import vars, funcs, log
import callbacks
import traceback, sys

# set up variables that will be overridden - populate them by default in case config doesn't load, but
global layer_files, export_pdf, export_png, export_mxd
layer_files = ["gen_1.lyr","gen_2.lyr","gen_3.lyr","gen_4.lyr"]
export_pdf = True
export_png = True
export_mxd = True

def mapping_process_config():
    if export_pdf is False:
        log.write("PDF Export disabled via export_pdf config variable - PDFs will not be generated",1)
    if export_png is False:
        log.write("PNG Export disabled via export_png config variable - PNGs will not be generated",1)
    if export_mxd is False:
        log.write("MXD Export disabled via export_mxd config variable - MXDs will not be saved",1)

try:
    import config
    mapping_process_config()
except:
    log.error("unable to load config.py - using defaults")

map_fish = {} # stores fish common names indexed by FID, but only for the fish we will process
all_maps = [] # stores our map objects (class fish_map)
common_layers = [] # stores references to layers that are generic so that if we use the same query in multiple places, we keep one layer with that information and only process it once



class fish_map: # an individual map for a given fish. Each fish can have multiple maps, depending on the queries
    def __init__(self):
        self.map_layers = [] # array of map_layer class objects
        self.map_title = None
        self.short_name = None
        
        self.query_set = None # the set in the database that defines this map
        self.query_set_name = None
        self.base_mxd = None
        self.base_ddp_mxd = None
        
        self.callback = None
        self.callback_args = None
         
    def setup(self,queries,title,short_name,id,set_name,mxd,ddp_mxd,callback,callback_args,fish=None):
              
        self.map_title = title
        self.query_set = id
        self.query_set_name = set_name
        self.short_name = short_name
        self.base_mxd = mxd
        self.base_ddp_mxd = ddp_mxd
        self.callback_args = structure_args(callback_args)
        self.callback = callback
        
        for query in queries: # make a layer in this map for each query
            self.map_layers.append(map_layer(query,fish,self))
        
        self.process_map_title() # do this after the layers are added because it will search through the layers for a fish - done this way so that it can be called another time. Calling it with the fish directly from above seems resource inefficient since it requires more code below
        
    def process_map_title(self): # map title should also support {mxd}, which then looks at the mxd, gets the title from there, and runs it through here as well, in case the mxd has a {FISH} block
        
        self.map_title = self.map_title.lower() #convert to lowercase so our check is easier
        if "{species}" in self.map_title: # if we have this operator
            for layer in self.map_layers: # iterate over the layers until we find a fish
                if not layer.custom_query.bind_var == None: # if we find one
                    self.map_title = self.map_title.replace("{species}",map_fish[layer.custom_query.bind_var]) # replace the {fish} portion of the map with this fish's common name
                    break
            else: # if we completed the loop without hitting the break, signaling that we found something
                raise vars.MappingError("{species} operator used in map title, but no queries in the map's body are associated with more than one fish. If you wish to put a fish's name in the title, consider hardcoding it")
                 
        self.map_title = string.capwords(self.map_title) #Put it into title case now
        self.map_title = self.map_title.replace(" Huc"," HUC")
        self.map_title = self.map_title.replace(" Huc12"," HUC12") #TODO - can these lines just be achieved with .upper() ???
            
    def populate(self,db_cursor):
        
        for layer in self.map_layers: # for every layer that's a part of this map
            if layer.zones == []: # if it's still an empty array - which it's possible it's not since layers might be shared
                layer.populate(db_cursor)
    
    def make_layers(self, zone_layer, db_cursor):
        initial_zones = zone_layer
        for layer in self.map_layers:
            zone_layer = initial_zones # on every iteration of the loop, start fresh. It's likely better to just not share the name below so that we don't have to do this         
            if layer.cache_file == None: # again, if this isn't a shared layer
                
                if layer.zones == []: # if it's an empty array still
                    log.write("No Zones to map - skipping",1)
                    continue # make no layer - skip to the next layer. Otherwise, all zones will be selected. We'll handle the removal of empty layers later and skipping empty maps
                              
                layer.make(zone_layer,db_cursor)
                layer.cache_file = cache_layer(zone_layer, layer.custom_query.bind_var, layer.custom_query.id, db_cursor)
                        
            if layer.cache_file == None: # if we still don't have this defined
                raise vars.MappingError("No layer was created - skipping")
    
    def generate(self, ddp = False): # generates the map once it is set up
        log.write("\nGenerating Map for set %s - Map title %s" % (self.query_set_name,self.map_title),1)
            
        mxd = self.choose_mxd(ddp)
        
        if self.has_contents() is False: # if this map has no contents
            return # then don't bother continuing - we don't care about it
        
        # sort layers by rank
        if len(self.map_layers) > 1: # if we have multiple layers, make sure they are sorted
            self.map_layers = sorted(self.map_layers, key=lambda map_layer: map_layer.custom_query.rank, reverse=True) # we want it reversed because it's a stack so we want to place #4 below #3, etc
        
        # get the data frame
        dataFrame = arcpy.mapping.ListDataFrames(mxd)[0] #TODO: WARNING - this won't handle MXDs with multiple data frames - @UndefinedVariable
        
        #find the reference layer
        r_layer = self.find_reference_layer(mxd) # searches to find the blank layer. We'll use it first, then add more
        
        generic_layer_num = 0
        
        extent_object = None # set it to a blank for now
        
        #add the layers to the map
        for layer in self.map_layers:
            
            if layer.cache_file == None: # if this layer has no data, skip it
                print "No data - skipping"
                continue
            
            if layer.custom_query.layer_file == None or layer.custom_query.layer_file == "default": # if we don't have a custom layer file specified
                if generic_layer_num < len(layer_files): # then iterate through the generic ones we have for as long as we have them
                    layer.custom_query.layer_file = os.path.join(vars.internal_workspace,"mxds","base",layer_files[generic_layer_num]) 
                    generic_layer_num = generic_layer_num + 1
                else: # if we don't have any more default layers, but we need one, skip the layer and log that
                    log.write("No layer file specified and no default layers to use for layer in map %s - skipping" (self.map_title),1)
                    continue
                
            l_layer = arcpy.mapping.Layer(layer.custom_query.layer_file) # make the layer into an accessible file @UndefinedVariable
            l_layer.name = layer.custom_query.layer_name
                       
            # set the data source
            file_only = os.path.split(layer.cache_file)
            file_only = file_only[-1]
            try:
                l_layer.replaceDataSource(vars.layer_cache,"FILEGDB_WORKSPACE",file_only)
            except:
                raise
                vars.MappingError("Unable to set data source on map layer")

            # track the extents so that we can set it easily later without re-iterating over these
            if extent_object == None:
                extent_object = l_layer.getExtent() # start with the extent of the first layer
            else:
                self.track_extent(extent_object,l_layer)

            #insert the data
            arcpy.mapping.InsertLayer(dataFrame,r_layer,l_layer,"AFTER") # @UndefinedVariable
                          
        arcpy.mapping.RemoveLayer(dataFrame,r_layer) # we don't actually want that in there - it's just a marker @UndefinedVariable
        
        try:                
            #set text elements
            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"): #@UndefinedVariable
                if elm.text == "{Title}":
                    elm.text = self.map_title
                elif elm.text == "{Scientific Name}":
                    for layer in self.map_layers: # iterate over the layers until we find a fish
                        if not layer.custom_query.bind_var == None: # if we find one
                            if vars.all_fish.has_key(layer.custom_query.bind_var):
                                elm.text = vars.all_fish[layer.custom_query.bind_var].sci_name # replace the {fish} portion of the map with this fish's common name
                                break
                elif "{Date}" in elm.text:
                    l_time = time.strftime('%Y/%m/%d', time.localtime())
                    l_text = elm.text
    
                    l_text = string.replace(l_text,"{Date}",l_time)
                    elm.text = l_text
        except: # nonfatal for the map
            log.error("Unable to set text strings in map! You'll need to do that manually - see mapping.py line 162")
        # TODO: run the callback
                
        #set extent
        dataFrame.extent = extent_object
        #dataFrame.scale = dataFrame.scale * 1 # adds a nice bit of space around the edges
        
        self.export_maps(mxd,file_only,ddp,extent_object,dataFrame) #extent_object and dataFrame are passed in so we can grab the extent and check it with DDP
        
    def has_contents(self):
        
        for layer in self.map_layers:
            if not layer.cache_file == None: 
                return True # one of the layers has a file to pop onto the map! Great - the map has data
            
        return False # if iterating over every layer didn't cause us to return, then this map has...nooo data - return false
    
    def decrement_ref_counts(self):
        for index in range(len(self.map_layers)): # using this method in order to not copy out the data
            self.map_layers[index].ref_count = self.map_layers[index].ref_count - 1 
    
    def export_maps(self,mxd,file_only, ddp, extent_object, data_frame):
        
        if ddp == True:
            log.write("Exporting Data Driven Pages...This may take some time...",1)
        
        # construct filename base
        base_name = ""
        if not self.short_name == None: # if we have a short name, prepend it to the output
            base_name = base_name + self.short_name + "_"
        if ddp == True:
            base_name = base_name + "ddp_"
        base_name = base_name + file_only 
        
        # Export the files        
        mxd_out = os.path.join(vars.internal_workspace,"mxds","output","%s.mxd" % base_name)
                
        # Write an MXD so we can mess with this independently
        if export_mxd is True:
            log.write("Writing mxd %s" % mxd_out,1)
            try:
                mxd.saveACopy(mxd_out)
            except:
                log.error("Unable to save MXD for %s - ArcGIS threw an error" % mxd_out)
        
        if ddp is False: # no ddp export with PNGs at the moment...If this becomes important (hint, it will), then we can do this with a loop
            if export_pdf is True:
                # Write out the PDF
                pdf_out = os.path.join(vars.internal_workspace,"maps","output","%s.pdf" % base_name)
                log.write("Saving pdf %s" % pdf_out,1)
                try:
                    arcpy.mapping.ExportToPDF(mxd, pdf_out) #@UndefinedVariable
                except:
                    log.error("Unable to save PDF for %s - ArcGIS threw an error" % pdf_out)
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    log.error(repr(traceback.format_exception(exc_type, exc_value,exc_traceback)))
                
            # Write a PNG - allows for quick
            if export_png is True:
                png_out = os.path.join(vars.internal_workspace,"maps","output","%s.png" % base_name)
                log.write("Saving png %s" % png_out,1)
                try:
                    arcpy.mapping.ExportToPNG(mxd, png_out, resolution=300) #@UndefinedVariable
                except:
                    log.error("Unable to save PNG for %s - ArcGIS threw an error" % png_out)
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    log.error(repr(traceback.format_exception(exc_type, exc_value,exc_traceback)))
                
        else: # if it's ddp!
            log.write("Saving data driven pdfs and pngs",1)
            l_out_dir = os.path.join(vars.internal_workspace,"maps","output",base_name)
            if not os.path.exists(l_out_dir):
                os.mkdir(l_out_dir)

            for pageNum in range(1, mxd.dataDrivenPages.pageCount + 1): #shamelessly taken from esri
                if export_pdf is True:
                    mxd.dataDrivenPages.currentPageID = pageNum
                    print "%s..." % pageNum,
                    if self.layers_visible(extent_object,data_frame) is False:
                        log.write("Skipping data driven page %s - no data is visible" % pageNum)
                        continue
                    try:
                        arcpy.mapping.ExportToPDF(mxd, os.path.join(l_out_dir,base_name + "_" + str(pageNum) + ".pdf")) #@UndefinedVariable
                    except:
                        log.error("Unable to export PDF for %s" % base_name + "_" + str(pageNum) + ".pdf")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        log.error(repr(traceback.format_exception(exc_type, exc_value,exc_traceback)))
                
                if export_png is True:
                    try:
                        arcpy.mapping.ExportToPNG(mxd, os.path.join(l_out_dir,base_name + "_" + str(pageNum) + ".png"), resolution=150) #@UndefinedVariable
                    except:
                        log.error("Unable to export PNG for %s" % base_name + "_" + str(pageNum) + ".png")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        log.error(repr(traceback.format_exception(exc_type, exc_value,exc_traceback)))
        
        #TODO - Export a dataframe pdf that's large enough to use in a lot of instances
        
        print "\n", # writing newline in case the last line printed didn't have one
        
        del mxd # clean up a bit. We might still have some layers floating around. Arc is a bit ambiguous to that...
    
    def layers_visible(self,check_extent,data_frame): # this actually doesn't guarantee that it's visible - in the case of a feature with two points at the far corners of a bounding box (or features with that distribution. you can be at a spot inside the theoretical bounding box without data. Los Angeles NF could frequently be in this situation.
                
        #First, the simple check. Does the layer's endpoints fall in the extent
        if funcs.is_between(check_extent.XMin, data_frame.extent.XMin, data_frame.extent.XMax) or funcs.is_between(check_extent.XMax, data_frame.extent.XMin, data_frame.extent.XMax) or (funcs.is_between(data_frame.extent.XMin,check_extent.XMin,check_extent.XMax) and funcs.is_between(data_frame.extent.XMax,check_extent.XMin,check_extent.XMax)):
            # if either of the X values of the check extent object are between the x values of the data frame OR if the data frame is encapsulated in the feature extent
            # and then... check the same for the y values
            if funcs.is_between(check_extent.YMin, data_frame.extent.YMin, data_frame.extent.YMax) or funcs.is_between(check_extent.YMax, data_frame.extent.YMin, data_frame.extent.YMax) or (funcs.is_between(data_frame.extent.YMin,check_extent.YMin,check_extent.YMax) and funcs.is_between(data_frame.extent.YMax,check_extent.YMin,check_extent.YMax)):
                return True
            
        # Still not done - now we need to see if, possibly, the layer's endpoints are wrapped around the extents. Essentially, is the extent inside the layer.
        
        return False # if we get here, then the layers aren't visible in the data frame
    
    def track_extent(self,extent_object,layer):
        
        l_properties = layer.getExtent()
        
        # each of these essentially says that if this layer is further out to one direction than the current setting, change the setting
        if l_properties.XMin < extent_object.XMin:
            #print "Expanding extent east from %s to %s" % (extent_object.XMin,l_properties.XMin)
            extent_object.XMin = l_properties.XMin
        if l_properties.YMin < extent_object.YMin:
            #print "Expanding extent south from %s to %s" % (extent_object.YMin,l_properties.YMin)
            extent_object.YMin = l_properties.YMin
        if l_properties.XMax > extent_object.XMax:
            #print "Expanding extent west from %s to %s" % (extent_object.XMax,l_properties.XMax)
            extent_object.XMax = l_properties.XMax
        if l_properties.YMax > extent_object.YMax:
            #print "Expanding extent north from %s to %s" % (extent_object.YMax,l_properties.YMax)
            extent_object.YMax = l_properties.YMax
    
    def find_reference_layer(self, mxd):
        for lyr in arcpy.mapping.ListLayers(mxd): #@UndefinedVariable
            if lyr.isFeatureLayer:
                if lyr.datasetName == "blank_feature":
                    return lyr
        else: # if we still don't have an object, then we gotta skip this one! This would mean a programmatic error
            raise vars.MappingError("No layer to update.")
    
    def choose_mxd(self,ddp):
        if ddp is False: # if it's a normal map this time
            if self.base_mxd == "default" or self.base_mxd == None: # set the mxd - if a custom mxd wasn't specified, use the default
                self.base_mxd = vars.mxd_source 
            else:
                self.base_mxd = os.path.join(vars.internal_workspace,"mxds","base",self.base_mxd)
            return arcpy.mapping.MapDocument(self.base_mxd) # open the mxd  @UndefinedVariable
        else: # otherwise, use the DDP map
            if self.base_ddp_mxd == "ddp_default" or self.base_ddp_mxd == None: # is the map name already something else? If not, use the default
                self.base_ddp_mxd = vars.mxd_ddp_source
            else:
                self.base_ddp_mxd = os.path.join(vars.internal_workspace,"mxds","base",self.base_ddp_mxd)
            return arcpy.mapping.MapDocument(self.base_ddp_mxd) #@UndefinedVariable
    
class map_layer:
    def __init__(self,query,bind_v,parent = None):
        self.zones = [] # the HUCs returned from the database for this layer
        self.aux_attrs = [] # used in case each zone has a particular set of attributes to be used in post processing. The callback needs to know already the order it comes in though
        self.certainty = None # the certainty level of the data we've retrieved (for layer ordering)
        self.cache_file = None # the location of the cache file
        self.symbology_lyr = None
        self.layer_name = None # the name of the layer in memory

        self.parent_map = parent
        
        self.ref_count = 0 # a count of the number of references to this layer - if it goes back to zero, we'll nuke it after exporting.
        
        # CUSTOM QUERY        
        self.custom_query = custom_query(query.query_string,query.rank,query.id,query.layer_file,query.callback,query.callback_args,query.layer_name) # do it this way so we make a COPY of the query
        self.custom_query.bind_var = bind_v
            
        if "?" in query.query_string: # if this query string requires a bind variable
            if not bind_v == None: # Make sure we have one
                self.custom_query.bind_var = bind_v
            else: # but we don't have one! EXCEPTION
                raise vars.MappingError("Query string with bind variable called with no fish to bind - query string: %s, fish %s" % (query.query_string,fish))
        else: # if it doesn't require a bind variable - essentially,  it's a generic query
            self = check_common_layers(self) # passes itself in and probably gets itself back out. It's possible it will get out a layer that already exists in another map so that we save some work. It's possible the cost of checking this isn't worth it, but in most cases the array of common layers is unlikely to be large
        
    def populate(self,db_cursor):
        log.write("Processing Custom Query: %s with bind variable %s" % (self.custom_query.query_string,self.custom_query.bind_var),1)
        if self.custom_query.bind_var == None: # if we don't have a bind var, don't provide one!
            l_results = db_cursor.execute(self.custom_query.query_string) # execute its query
        else:
            self.custom_query.process_bind() # for queries where the bind variable is needed multiple times, this replaces {bind} with the variable
            l_results = db_cursor.execute(self.custom_query.query_string,self.custom_query.bind_var) # execute its query
            
        for result in l_results:
            self.zones.append(result.Zone_ID)
            self.aux_attrs.append(result) # full array, including Zone_ID is appended for access later. If the callback wants to access other information without a new query, this can handle that
    
    def make(self, zone_layer, db_cursor):
        try:
            log.write("Selecting Zones")
            selection_type = "NEW_SELECTION" # start a new selection, then add to
            try:
                if not (int(len(self.zones)) == int(arcpy.GetCount_management(zone_layer).getOutput(0))): # if they are the same, then skip the selection - this shortcut won't work if we change to allowing portions of a HUC string to select the HUCs
                    print "Selecting %s zones" % len(self.zones)
                    zone_expression = ""
                    for index in range(len(self.zones)): # we have to do this in a loop because building one query to make Arc do it for us produces an error
                        zone_expression = zone_expression + "[HUC_12] = '%s' OR " % self.zones[index] # brackets are required by Arc for Personal Geodatabases (that's us!)
                        if (index % 12 == 0 or index == len(self.zones)-1): # Chunking: every 12th HUC, we run the selection, OR when we've reached the last one. we're trying to chunk the expression. Arc won't take a big long one, but selecting 1 by 1 is slow
                            zone_expression = zone_expression[:-4] # chop off the trailing " OR "
                            arcpy.SelectLayerByAttribute_management(zone_layer,selection_type,zone_expression)
                            selection_type = "ADD_TO_SELECTION" # set it so that selections accumulate
                            zone_expression = "" # clear the expression for the next round
            except:
                raise vars.MappingError("Unable to select features for new layer - check the sql query associated with query id %s" % self.custom_query.id)
            
            try: # CALLBACKS - allow custom processing to occur after the layer has been pulled
                if not self.custom_query.callback == None: # if we have a callback
                    l_callback = getattr(callbacks, self.custom_query.callback) # get the callback function's object
                    zone_layer = l_callback(zone_layer, db_cursor,self.custom_query.callback_args, self) # call it with the layer as the parameter. It's possible that it may copy it out and return a new zone_layer
            except:
                raise vars.MappingError("Failed in callback for layer with query id %s" % self.custom_query.id)
            
            self.layer_name = zone_layer # store it for later - we'll cache based on this name
                        
        except vars.MappingError:
            raise
        except:
            if vars.debug == 1: raise
            raise vars.MappingError("Unable to make and save the new layer")

class custom_query:
    def __init__(self,cq = None,qr = None, qi = None,lf = None, cb = None, cba = None, ln = None):
        self.query_string = cq
        self.rank = qr
        self.id = qi
        
        self.bind_var = None # if we have a fish to use as a bind variable (multi-fish queries will have one), it's stored here
        
        self.layer_name = ln
        self.layer_file = lf # this is stored here because it's associated with the queries in the db before making the layers
        self.callback = cb # optional callback to be processed after results of this query get returned
        self.callback_args = structure_args(cba)
                
        # custom queries allow us to generate maps with custom layers that will always be processed for a given fish 
        # the default maps are stores as custom queries so that only one logic set is needed to make all of the maps
        # default maps are stored with FID ALL in order to be processed for all fish with data that are specified by this function   

    def process_bind(self): # in instances where we need multiple bind variables, the {bind} entity lets us add them in.
        if "{bind}" in self.query_string:
            self.query_string = self.query_string.replace("{bind}",str(self.bind_var))
        
def begin(fish_subset):
    
    log.write("\nBeginning Mapping",1)
    
    mapping_cursor,mapping_conn = funcs.db_connect(vars.maindb) # open the db for the remainder of this function
    
    log.write("Retrieving mapping data from database...",1)
    
    # handle fish specified or get fish ids if "all"
    global map_fish # use the global fish structure
    map_fish = get_fish_to_map(fish_subset, mapping_cursor) # takes the argument and returns a dictionary with codes set as the index - receives the cursor in case fish subset is all, in which case it retrieves all fish that have an observation
    del fish_subset
    
    global all_maps
    all_maps = initialize_maps(mapping_conn)
    
    zone_layer = refresh_zones() # if this layer doesn't exist, it makes it. Some of these functions modify the layer
    if vars.usecache == 0: # if we're not supposed to use the cache only
        for i in range(len(all_maps)):
            try:
                all_maps[i].populate(mapping_cursor)
                all_maps[i].make_layers(zone_layer,mapping_cursor)
                
                #if we've made it to the end of the processing here, we can commit any changes we've made to the layer cache, etc
                mapping_conn.commit()
            except vars.MappingError as e:
                #if vars.debug == 1: raise
                log.write("Encountered error in mapping id #%d - reported \"%s\". Skipping" % (all_maps[i].query_set,e),1)
                all_maps[i] = None # zero out the map
                continue
    else: # we're supposed to use the cache
        for map in all_maps:
            for layer in map.map_layers: #then for every layer in every map
                    layer.cache_file = cache_layer(None,layer.custom_query.bind_var,layer.custom_query.id,mapping_cursor) # get the quick cache file name for mapping
        
    log.write("Generating maps",1)
    for index in range(len(all_maps)): # Doing this as a second loop so that we have some certainty in this - if we reach this point, layer generation and caching is complete
        if not all_maps[index] == None: 
            try:   
                all_maps[index].generate()
                
                if not all_maps[index].base_ddp_mxd == None: # if we also need to do one with Data Driven Pages...
                    all_maps[index].generate(ddp = True)
            except:
                raise
            
            all_maps[index].decrement_ref_counts()
            all_maps[index] = None # see if we can't fix the memory leak in arcgis - we don't need this anymore - maybe deleting it will help, but we don't wan to delete the actual array element (or else we end up out of range later)
            clean_common_layers()
        
    funcs.db_close(mapping_cursor,mapping_conn)
    
    log.write("Mapping Complete",1)
    
def initialize_maps(db_conn,set_ids = []):
    
    log.write("Initializing map structures")
    
    db_cursor = db_conn.cursor()
    l_maps = [] # local map array
    
    l_query_sets = get_query_sets(db_cursor,set_ids) # returns a database results object to process below

    for result in l_query_sets:
        l_queries = []
        
        try:
            l_queries = get_custom_queries(result.ID,db_conn) # returns all of the queries to be used in this kind of map
        except vars.MappingError as error:
            log.error("%s - skipping map" % error)
            continue # skips this map - it won't make it to be appended to the list
        except:
            log.error("Problem retrieving custom queries - skipping map set %s" % result.Short_Name)

        query_fish = get_multi_fish_query(result.ID,db_conn,result.Iterator) # return the bind values to run this query set for
        
        if not query_fish == None and len(query_fish) > 0 : # if this is supposed to be done for multiple fish - the second check might be unnecessary
            # select fish from fish table, check against our fish list that was passed in, and set up objects
            for fish in query_fish:
                try:
                    l_map = fish_map() # init a new map
                    l_map.setup(l_queries,result.Map_Title,result.Short_Name,result.ID,result.Set_Name,result.Base_MXD,result.DDP_MXD,result.Callback,result.Callback_Args,fish)
                except vars.MappingError as e: # if we have any problems during setup, then we need to skip this map
                    log.error("Skipping Query Set %s with bind variable %s - encountered problem during setup - error reported was %s" % (result.ID,fish,e))
                    continue

                l_maps.append(l_map)
        else:
            try:
                l_map = fish_map()
                l_map.setup(l_queries,result.Map_Title,result.Short_Name,result.ID,result.Set_Name,result.Base_MXD,result.DDP_MXD,result.Callback,result.Callback_Args)
                # set up a single object
            except vars.MappingError as e: # if we have any problems during setup, then we need to skip this map
                log.write("Skipping Query Set %s - encountered problem during setup - error reported was %s" % (result.ID,e), 1)
                continue
            
            l_maps.append(l_map)
    
    db_cursor.close()
    
    return l_maps

def get_query_sets(db_cursor,set_ids):
    
    l_map_query = "select ID, Map_Title, Set_Name, Short_Name, Base_MXD, DDP_MXD, Iterator, Callback, Callback_Args from defs_Query_Sets where Active = True"
    l_map_query_extend = ""
    if type(set_ids).__name__ == "list" and len(set_ids) > 0:
        l_map_query_extend = "where "
        for item in set_ids:
            l_map_query_extend = l_map_query_extend + "ID = %d OR " % item
        l_map_query_extend = l_map_query_extend[-4:] # chop off the final " OR "
    l_map_query = l_map_query + l_map_query_extend
    
    l_results = db_cursor.execute(l_map_query)
    
    return l_results
        
def get_custom_queries(query_set,db_conn):
    
    log.write("Getting custom queries for set %s" % query_set)
    
    db_cursor = db_conn.cursor()
    
    l_sql_query = "select mq.Custom_Query, mq.Query_Rank, mq.ID, mq.Layer_File, mq.Callback_Function, mq.Callback_Args, mq.Layer_Name from Map_Queries as mq where mq.Query_Set = ?"

    db_cursor.execute(l_sql_query,query_set)
    l_queries = db_cursor.fetchall()
    
    if not len(l_queries) > 0:
        raise vars.MappingError("No queries for query set %s" % query_set)
    
    query_objects = []
    for item in l_queries:
        t_query = custom_query(item.Custom_Query,item.Query_Rank,item.ID,item.Layer_File,item.Callback_Function,item.Callback_Args,item.Layer_Name)
        query_objects.append(t_query)
    
    db_cursor.close()
    return query_objects
    
    # should return an array of custom query objects       
        
def get_multi_fish_query(query_set, db_conn, bind_column = None):
    db_cursor = db_conn.cursor()
    
    l_query = "select Bind_Value from Query_Bind where Query_Set_ID = ?"
    db_cursor.execute(l_query,query_set)
    
    # Check values against fish we were told to process
    
    query_bind = db_cursor.fetchone()
    
    if query_bind == None: # if we don't have a row, then this query stands alone
        return None
  
    if query_bind.Bind_Value == "all": # if this query is supposed to be run for all values
        if bind_column == None or bind_column == "Species:FID":
            return map_fish.keys() # set the fish we want to process
        else:
            return get_bind_values(bind_column,db_cursor) # retrieve the bind values based upon the column
    else:
        ### print "getting SELECTed fish"
        query_bind_ids = db_cursor.fetchall()
        query_bind_ids.append(query_bind) # we need to add it to the end since it wasn't "all" and fetchall() only returns unfetched rows
        
        query_bind = []
        for item in query_bind_ids: # this time, it's supposed to be a loop, but we didn't want that if on every iteration
            # cross-check these fish against the fish list we started with. Remove the ones that aren't in there.
            if map_fish.has_key(item.Bind_Value):
                query_bind.append(item.Bind_Value)
    
    db_cursor.close()
    return query_bind
          
def get_bind_values(bind_column, db_cursor):
    table_col = bind_column.split(":")
    try:
        table = table_col[0]
        col = table_col[1]
    except:
        raise vars.MappingError("Unable to select bind values")

    l_string = "select distinct %s from %s" % (col,table)
    results = db_cursor.execute(l_string)
    
    values = []
    for item in results:
        values.append(item[0])
        
    return values

def get_fish_to_map(fish_subset,db_cursor): # takes the argument to mapping and determines what fish we are mapping - returns an array of fish ids
    # TODO: Theoretically, it'd be good if this function checked to make sure that we have data on each fish specified when a list is given
        
    log.write("Determining fish to map")
    map_fish = {}
    
    if fish_subset == "all":    
        map_fish = get_mappable_fish(db_cursor)
    elif type(fish_subset).__name__ == "string" and len(fish_subset) > 0: # if they provided a valid string of just one fish
        l_fish = fish_subset # save the value
        fish_subset = [] # make it a list so we can use the following code no matter what
        fish_subset[0] = l_fish
    
    if type(fish_subset).__name__ == "list" and len(fish_subset) > 0: # if a list of fish was provided and it's not empty
        for fid in fish_subset:
            l_query = "select Common_Name from Species where FID = ?"
            l_result = db_cursor.execute(l_query, fid)
            map_fish[fid] = l_result[0].Common_Name # make the dictionary of fish indexed by FID
   
    if len(map_fish) == 0: # if we still have no fish
        raise vars.MappingError("Unable to determine the fish to map! Valid options are \"all\", an array subset of species ids or a string containing a species id")
    
    return map_fish
    
def get_mappable_fish(db_cursor): # returns all the fish we have observations for
    #  should also check to only select fish that have new observations. when importing data we should set a flag. That way we know which fish are "up to date" and won't reprocess maps that are unaffected
    l_items = {}
    l_query = "select distinct Observations.Species_ID, Species.Common_Name from Observations, Species where Observations.Species_ID = Species.FID"
    l_results = db_cursor.execute(l_query)
    for fish in l_results:
        l_items[fish.Species_ID] = fish.Common_Name
    
    return l_items

def check_common_layers(layer):
    
    global common_layers # we might append, so we should specify that we're using the global version
    
    for index in range(len(common_layers)): # iterate over all of the common layers
        if layer.custom_query.query_string is common_layers[index].custom_query.query_string and \
        layer.custom_query.bind_var == common_layers[index].custom_query.bind_var: #if it's the same query, with the same bind var, and with the same callback - we're using "is" for the query string because that's going to come in once for each query set, but it will exclude query sets that have the same query elsewhere, but maybe with different callbacks since they won't reside in the same query space in memory
        # defunct piece of code now: saving, just in case...    and layer.custom_query.callback == check_layer.custom_query.callback
            common_layers[index].ref_count = common_layers[index].ref_count + 1
            return common_layers[index] # if we do, give this map that layer
        
    layer.ref_count = 1 # set a ref_count so that we can nuke shared layers when it hits zero. The software currently crashes after running too long, so we want to manage this
    common_layers.append(layer) # if we haven't returned yet, then this layer is a potential common layer that we haven't processed. Add it so that future layers check here
    return layer

def clean_common_layers():
    global common_layers
    
    l_max = len(common_layers)
    index = 0
    while index < l_max:
        if common_layers[index].ref_count == 0:
            del common_layers[index] # only deletes this reference, but we'll probably delete the others too
            continue # don't increment - the next layer will now be this index
        index = index + 1

def refresh_zones():

    zone_layer = "z_layer"
    try: # try to make it
        arcpy.MakeFeatureLayer_management(vars.HUCS, zone_layer) # bring the HUCs in as a layer
    except: # if we get an exception, we don't care because it will come out as an error later
        raise vars.MappingError("Couldn't load zones!")
    
    return zone_layer

def structure_args(args): # takes the arguments and makes them into a tuple
    if not type(args).__name__ == "list" and not args == None:
        if "::" in args: # if it has multiple args
            all_args = string.split(args,"::")
            return all_args # return the split
        else:
            return args # return the input
    else: # in the event that these have already been processed
        return args
            
def cache_layer(arc_layer, bind_var, query_id, db_cursor): # when called with arc_layer = None, returns full_layer_path immediately after it's generated. This way, we can use one spot to generate cache names, and return what would have been done with a full processing
    
    log.write("Caching layer",1)
    #check to see if this is already cached. If it is, remove the old file, save the new file and update the location
    out_layer_name = None
    
    if bind_var == None:
        out_layer_name = "layer_q" + str(query_id)
        bind_var = "NULL"
    else:
        out_layer_name = "f_%s_%s" % (bind_var,query_id) # can't start with a digit
    
    full_layer_path = os.path.join(vars.layer_cache,out_layer_name) # set the full path to the layer on disk
    
    if arc_layer == None: # if we don't actually want it to cache it - we just want the name
        if arcpy.Exists(full_layer_path): # we're looking for the name, but if it doesn't exist, then we don't want it because other things rely on that info
            print "Using cached layer"
            return full_layer_path
        else: # return None if we don't have it
            return None
    
    #l_sql = "select Layer_Cache.ID from Layer_Cache where Layer_Cache.Query_ID = ? and Layer_Cache.Bind_Var = ?" 
    #l_results = db_cursor.execute(l_sql,) # look to see if we have an existing layer for this query/bind var
    
    #for result in l_results:
    #    if not result.ID == None: # if there already is a stored result for this query/bind var
    try:
        if arcpy.Exists(full_layer_path): # if it also exists in the cache area
            arcpy.Delete_management(full_layer_path) # remove the old feature
        l_sql = "delete from Layer_Cache where Query_ID = ? and Bind_Var = ?"
        db_cursor.execute(l_sql,query_id,bind_var) # and delete the row
    except:
        raise vars.MappingError("Error removing the previous dataset for this query. Skipping this map. Data may have been deleted from the layer cache for query id %s with bind variable %s" % (query_id,bind_var))
    
    # regardless, we need to save the new data and update the database
    try:
        arcpy.CopyFeatures_management(arc_layer,full_layer_path) # save the new layer
    except:
        raise vars.MappingError("Unable to save the selection to the layer cache - unable to proceed with this map")
    
    try:
        l_sql = "insert into Layer_Cache (Query_ID,Bind_Var,Layer_File,Last_Updated) values (?,?,?,Now())"
        db_cursor.execute(l_sql,query_id,bind_var,out_layer_name) # add a record for it to the database
    except:
        raise vars.MappingError("Unable to update the Layer_Cache table in the database with the new file information")
   
    if not arc_layer == "z_layer":  # TODO: This needs to be more robust. hardcoding the name here is bad. Much better to have some other method of determining what to keep and what to remove (this goes back to the problem of keeping the layer in memory in the first place...it's a bit of a kluge
        try:
            arcpy.Delete_management(arc_layer) # do some cleanup - keeping all of this in memory is probably unwise - we'll read it back in when we need it
        except:
            print "Warning: Unable to delete layer %s from memory. The layer is not being skipped, but memory usage could rapidly increase if you see many of these messages" % arc_layer
    
    return full_layer_path
        
        