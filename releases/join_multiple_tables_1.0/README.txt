This script reads in an entire geodatabase of tables and joins those tables into one based upon a common key (just as any other join would work).
It outputs a table either in a user specified location or, if one is not specified, a new geodatabase.

It is recommended that you use a table in a file geodatabase for the output because it has the highest column limit (65534) as opposed to personal geodatabase (254), etc.
You can specify a geodatabase only, an empty string, or a specific table in a geodatabase for output. If it is a geodatabase, a table named megatableXX will be created
where XX is as many digits as are required to make the name unique. If you specify nothing, then a geodatabase will be created in the folder the script is run from and 
it will contain a table named megatableXX

See the configuration variables at the top of the script for input and output configuration. By default, it only joins field names found in a list of fields in the config
section. These fields are prefixed by the table's original name in the final output. If you want to join all fields, regardless of name, contact Nick Santos. This script
is not currently designed to do that, but could probably do it pretty easily.