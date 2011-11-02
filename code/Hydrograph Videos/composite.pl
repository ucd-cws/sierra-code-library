use warnings;

# conventions used here: variables prefixed by l are local, variables prefixed by r are references (as opposed to values)
# 							variables prefixed by both (eg my $lr_var_name) are both local and a reference.

use Cwd;
use File::stat;
use Time::Local;

my $hydrograph_duration = 9; # seems to be unused... ignore for now

my $l_dir = getcwd; # load the folder that this script is located in
my $graph_folder = $l_dir . "\\graphs"; # variable to store the subdirectories
my $pics_folder = $l_dir . "\\pics";
my $output_folder = $l_dir . "\\composited";

opendir(GRA,$graph_folder); # loads a directory to read the contents
my @graphs = readdir(GRA); # read the contents of the folder into the array @graphs
close(GRA); # close the directory

@graphs = sort @graphs; # order them appropriately, in case the OS didn't
shift @graphs; #remove "."
shift @graphs; #remove ".."

@graphs = index_graphs(\@graphs); # pass graphs by reference and overwrite them

opendir(PICS,$pics_folder); # same deal, but this time for the pictures
my @pics = readdir(PICS);
close(PICS);

@pics = sort @pics; #same as above

my $graph_index = 0; # tracks which graph we are on
my $g_time_low = 0; # $g_time_low stores the date in unix time of the earliest time on a given day
my $g_time_high = 0; # and $g_time_high stores the latest time (11:59pm) of the same day - together they give us a boundary of times for that day so that we can look for times on images and match them to the day.

for(my $i = 0;$i<@pics;$i++){ # for every picture in the folder
	###
	### Basically, this loops through all of the images and uses the hydrograph whose time boundaries (see above) include the image, then it composites them into the output folder
	###
	
	print "$pics[$i]\n"; # print its name
	
	my $mdate = 0;
	#get the image date
	$pics[$i] =~ /.*?_(\d+)$/; # looks for a name with a bunch of digits at the end
		$mdate = stat("$pics_folder/$pics[$i]")->mtime; # get the modification time of the picture
	
	# sanity check - is it an image?
	if (!($pics[$i] =~ /\.jpg$|\.png$/i)) {
		print "Not an image\n";
		next; # if it's not an image (namely, it's probably a directory) skip it
	}
	
	$graph = find_graph($mdate, \@graphs);
	
	if ($graph == 0){
		print "No graph! Probably an error\n";
		next;
	}
	
	my $out_name = "$output_folder/" . substr($pics[$i],0,length($pics[$i])-4) . "_composited.jpg"; # this use of substr strips the extension off so that we can modify the name
	
	
	my $full_pic = "$pics_folder/$pics[$i]"; # merge the names of the image and the folder so we have a full path
	my $full_graph = "$graph_folder/".$graph->{'name'}; # same with the graph
	
	system("composite -gravity NorthEast \"$full_graph\" \"$full_pic\" \"$out_name\""); # then make the system call to imagemagick to composite the two images and write them out to the file in $out_name - this puts the graph in the top right. We can change that by changing NorthEast to NorthWest, etc. We can also do more fine-grained control of location
	
	print "Next..\n\n";

}

sub get_graph_time{
	my $graph = shift; # get the graph name from the parameters
	
	$graph =~ /.*?(\d{4})\-(\d{2})\-(\d{2})\.png$/; # get the date information from the filenames of the graphs
	my $g_year = $1; 
	my $g_month = $2;
	my $g_day = $3;

	$g_month--; # 0 indexed so we need to subtract one from every month to get the human version
	
	if ($g_month < 0 || $g_month > 11 || $g_day < 0 || $g_year < 0){ # basic boundary checks...
		return 0, 0;
	}
	
	my $g_time_low = timelocal(0,0,0,$g_day,$g_month,$g_year); # Get the unix time representation of 12am on that day
	my $g_time_high = $g_time_low + 3600*24; # then get the unix time representation of 11:59 pm on that day
	
	return $g_time_low,$g_time_high; # send them back to the calling function

}

sub preprocess_images{
	# renames the images with the time so that we can process them into infinity!
}

sub index_graphs{
	
	my $lr_graph_names = shift;
	my @graphs = [];
	
	# individual_graph is a hash of l_time, h_time, name (=minimum time, maximum time, graph name)
	#my %graph_base = {};
	#$graph_base{"l_time"} = 0;
	#$graph_base{"h_time"} = 0;
	#$graph_base{"g_name"} = 0;
	
	print "indexing the graphs!\n";
	
	for(my $i=0;$i<@$lr_graph_names;$i++){
		$graphs[$i] = {};
		my ($l_time_low, $l_time_high) = get_graph_time($lr_graph_names->[$i]);
		if ($l_time_low == 0){
			print "skipping " . $lr_graph_names->[$i] . " - invalid timestamp in filename\n";
			next; # skip this iteration of the loop - this graph is out of bounds
		}
		$graphs[$i]{'l_time'} = $l_time_low;
		$graphs[$i]{'h_time'} = $l_time_high;
		$graphs[$i]{'name'} = $lr_graph_names->[$i];
		
		print $graphs[$i]{'name'} . " " . $graphs[$i]{'l_time'} . " " . $graphs[$i]{'h_time'} . "\n";
	}
	
	print "finished indexing\n\n\n";
	return @graphs;
}

sub find_graph{
	my $l_time = shift;
	my $lr_graphs = shift;
	
	print "finding graph...";
	for (my $i = 0;$i<@$lr_graphs;$i++){	# for every element in the graphs index
		if ($l_time > $lr_graphs->[$i]{'l_time'} && $l_time < $lr_graphs->[$i]{'h_time'}){ # if the time is in bounds
			print "found!\n";
			return $lr_graphs->[$i];  # note - this returns the actual graph, not a reference!
		}
	}
	return 0;
}
