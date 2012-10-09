This code lives in the map document SRSS_b.mxd in a button called "Run SRSS"

It was originally written for an older version of ArcMap, and was ported by the author (Nate Roth at ICE) to ArcGIS 10.0.

The code is VBA, written by Nate Roth at ICE. It requires a (free) VBA license for ArcMap as well as separate installation of the VBA tools from the ArcGIS Desktop disk

See the email below for more from Nate on using it:


-----------------------------------------

I’ve attached the mxd with embedded code and a sample dataset in the .7z file. Use 7-zip, a free, open source compression program  to unzip it. Campus email has started stripping .zip files with mxds that have vba code out of emails. I remember fondly getting up really early in the morning in the spring of 2004 to “validate” the sunrise results of the model before going spring skiing in the backcountry there…


On that note, please confirm that you’ve received this because I’m never sure if the campus might have “disappeared” emails with embedded code.
 

Ok, here we go…

Some of the internal error checking has been disabled, because I’d have had to rewrite a fair amount of it. The field and featureclass type constants seem to have changed since 8.3 when the original code was written and 10.0 which I’m using now.

 
It’s always painful to go back and look at some of your early code and see how very primitive it is. It would be written very differently if I were to redo it now. It definitely wouldn’t be written in VBA… Speaking of which. If you’re using arcgis 10.0 or 10.1 you’ll need to request the VBA license from ESRI (or our campus site license coordinator as appropriate) and install VBA because it’s no longer part of the default installation of arcgis. It is included on the media for 10.0 and 10.1 and the license is a free one.

 
Input data.

A digital elevation model (raster) with units in meters (x, y, and z) I wrote it around a UTM projection, though California albers would work fine too.

A feature class with one polygon feature that defines the boundary of the analysis area. This must be in a geographic projection. I pull the centroid from this boundary to set the reference point for the altitude and azimuth of the sun over the area.

A sample point file which must be a point feature class with at least one field to use as an ID. This field must be independent of the ObjectID field. When I wrote the code I was on an “avoid using the OID directly” kick.

 
For the Table Name don’t include the “.dbf” that will be appended automatically.

When asked to specify the output raster location, just point it to an empty folder.
 

The time interval is in 100ths of an hour. Inconvenient, I know, but I didn’t convert them to base 60. This means that 100 means it’ll iterate every hour, 50 every half hour, … and 5 will be every 3 minutes (1/20th of an hour).