#! /usr/bin/env python2

def main():


    #
    # Imports & globals
    #
    import pysam, sys, time
    global args, summaryInstance, output_tagged_bamfile

    #
    # Argument parsing
    #
    argumentsInstance = readArgs()
    processor_count = readArgs.processors(argumentsInstance)

    #
    # Initials
    #
    summaryInstance = Summary()

    #
    # Progress
    #
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tReading input file and building duplicate position list\n')

    #
    # Data processing & writing output
    #

    # read duplicate file and build position list which is to be investigated.
    duplicate_position_dict = dict()
    infile = pysam.AlignmentFile(args.input_tagged_bam, 'rb')
    current_read_count = 1000000
    for read in infile.fetch(until_eof=True):

        summaryInstance.totalReadPairsCount += 1
        if summaryInstance < summaryInstance.totalReadPairsCount:
            sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\t' + "{:,}".format(current_read_count) + ' pairs read\n')
            current_read_count += 1000000

        # Only fetch positions marked as duplicates
        if not read.is_duplicate: continue
        else:
            summaryInstance.totalReadPairsMarkedAsDuplicates += 1

        try: duplicate_position_dict[read.reference_name]
        except KeyError:
            duplicate_position_dict[read.reference_name] = dict()

        # fetch barcode
        cluster_id = read.query_name.split()[0].split('_')[-1].split(':')[-1]
        try: duplicate_position_dict[read.reference_name][read.pos].append(int(cluster_id))
        except KeyError:
            duplicate_position_dict[read.reference_name][read.pos] = [int(cluster_id)]

    infile.close()

    #
    # Progress
    #
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tDuplicate position list built\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tTotal mapped read pair count: ' + "{:,}".format(summaryInstance.totalReadPairsCount) + '\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tReducing duplicate dictionary (proximity)\n')

    window = 100000
    proximity_duplication_dict_with_chromosomes = reduce_dict(duplicate_position_dict, window)  # Window is the strict cutoff value for how far a read can be for it being in the same cluster id.

    #
    # Progress
    #
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tDuplicate dictionary reduced\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tBuilding merging dictionary\n')

    merge_dict = dict()

    # Builds merge_dict from positions
    for chromosome, proximity_duplication_dict in proximity_duplication_dict_with_chromosomes.items():

        duplicate_position_list = sorted(proximity_duplication_dict.copy().keys())
        max_j = len(duplicate_position_list)

        #
        # Progress
        #
        sys.stderr.write('\n' + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\t' + str(chromosome) + '\n')
        sys.stderr.write('|------------------------------------------------|\n')
        two_percent = int(max_j/50)
        current_percentage = two_percent

        for i in range(len(duplicate_position_list)-2):

            if current_percentage < i:
                sys.stderr.write('#')
                current_percentage += two_percent
            j = i + 1
            unchecked_positions = list()
            unchecked_positions_set = set()
            current_match_dict = dict()


            # Continue loop until all duplicates have been saved in merge dict for the current window.
            # Extends window if duplicate is found
            while True:

                # Returns list of matching clusterid:s
                # Does not discriminate between window/extended window
                new_matches_clusterid = match_clusterid(duplicate_position_dict[chromosome][duplicate_position_list[i]], duplicate_position_dict[chromosome][duplicate_position_list[j]])

                if not len(new_matches_clusterid) == 0:
                    # Keeps track of matching clusterid and their positions for the current phase window.
                    try: current_match_dict[duplicate_position_list[i]] = current_match_dict[duplicate_position_list[i]].union(new_matches_clusterid)
                    except KeyError:
                        current_match_dict[duplicate_position_list[i]] = set(new_matches_clusterid)
                    try: current_match_dict[duplicate_position_list[j]] = current_match_dict[duplicate_position_list[j]].union(new_matches_clusterid)
                    except KeyError:
                        current_match_dict[duplicate_position_list[j]] = set(new_matches_clusterid)

                # Check if new positions have been found
                if len(new_matches_clusterid) >= 1:
                    for match_pos in new_matches_clusterid:
                        unchecked_positions_set.add(match_pos)
                    unchecked_positions = sorted(unchecked_positions_set) # Converting back to list and sorting
                    new_matches_clusterid = []

                    remove_from_set = unchecked_positions[0]
                    unchecked_positions = unchecked_positions[1:]
                    unchecked_positions_set.remove(remove_from_set)
                    j = j + 1

                # Checks if old positions need to be investigated.
                elif len(unchecked_positions) >= 1:
                    remove_from_set = unchecked_positions[0]
                    unchecked_positions = unchecked_positions[1:]
                    unchecked_positions_set.remove(remove_from_set)
                    j = j + 1

                else:
                    merge_dict = report_matches(current_match_dict, merge_dict, chromosome)#, duplicate_position_list)
                    break

                # Checks if j is about to be out of range for list
                if j >= max_j:
                    merge_dict = report_matches(current_match_dict, merge_dict, chromosome)#, duplicate_position_list)
                    break

    #
    # Progress
    #
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tMerging dictionary built\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tReducing merging dictionary (several step redundancy)\n')

    # Reduces merge_dict cases where {5:3, 3:1} to {5:1, 3:1} since reads are not ordered according to cluster id.
    for cluster_id_to_merge in sorted(merge_dict.copy().values()):

        # Try to find value for
        try: lower_value = merge_dict[merge_dict[cluster_id_to_merge]]
        except KeyError:
            continue

        higher_value = merge_dict[cluster_id_to_merge]
        del merge_dict[cluster_id_to_merge]
        merge_dict[cluster_id_to_merge] = lower_value
        merge_dict[higher_value] = lower_value

    #
    # Progress
    #
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tMerging dictionary reduced\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tWriting output file\n')
    sys.stderr.write('|------------------------------------------------|\n')
    two_percent = int(summaryInstance.totalReadPairsCount/50)
    current_percentage = two_percent

    # Saves merging history (later written to log file)
    summaryInstance.reportMergeDict(merge_dict)

    counter = int()
    for clusterid_to_remove in merge_dict.keys():
        counter += 1
    summaryInstance.ClustersRemovedDueToMerge = counter

    # Translate read file according to merge_dict (at both RG tag and in header)
    infile = pysam.AlignmentFile(args.input_tagged_bam, 'rb')
    out = pysam.AlignmentFile(args.output_bam, 'wb', template=infile)
    for read in infile.fetch(until_eof=True):

        if current_percentage < current_percentage:
            sys.stderr.write('#')
            current_percentage += two_percent

        # If RG tag i merge dict, change its RG to the lower number
        try: read_tag = str(merge_dict[int(dict(read.tags)['RG'])])
        except KeyError:
            read_tag = None

        if read_tag:
            read.set_tag('RG', read_tag, value_type='Z')
            read.query_name = '_'.join(read.query_name.split('_')[:-1])+'_RG:Z:'+read_tag
            summaryInstance.readPairsMerged += 1

        out.write(read)

    infile.close()
    out.close()

    #
    # Progress
    #
    sys.stderr.write('\n')
    sys.stderr.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\tFinished\n')
    summaryInstance.writeLog()

def reduce_dict(unfiltered_position_dict, window):
    """ Removes sorted list elements which are not within the window size from the next/previous entry and formats to
    dict instead of list."""

    filtered_position_dict = dict()
    for chromosome, contig_dict in unfiltered_position_dict.items():

        try: filtered_position_dict[chromosome]
        except KeyError:
            filtered_position_dict[chromosome] = dict()

        add_anyway = False
        unfiltered_position_list = list(contig_dict.keys())

        for i in range(len(unfiltered_position_list)-1):
            position=unfiltered_position_list[i]
            next_pos=unfiltered_position_list[i+1]

            if position == next_pos: # The other sequence, fetches sequences for values later
                pass

            elif (position+window) >= next_pos:
                filtered_position_dict[chromosome][position] = contig_dict[position]
                add_anyway = True

            elif add_anyway:
                filtered_position_dict[chromosome][position] = contig_dict[position]
                add_anyway = False

            else:
                pass

        if add_anyway:
            filtered_position_dict[chromosome][position] = contig_dict[position]

    #
    # Stats
    #
    #summaryInstance.duplicatePositionWithoutProximity = len(unfiltered_position_dict.values().values()) - len(filtered_position_dict.values().values())

    return filtered_position_dict

def match_clusterid(clusterid_list_one, clusterid_list_two):
    """ Takes two lists returns matching entries between the two. """

    match_set = set()
    for clusterid_one in clusterid_list_one:
        for clusterid_two in clusterid_list_two:

            if clusterid_one == clusterid_two:
                match_set.add(int(clusterid_one))

    match_sorted_list = sorted(match_set)
    return match_sorted_list

def report_matches(current_match_dict, merge_dict, chromosome):#, duplicate_position_list):
    """ Reports matches by updating merge_dict with newfound matches. Dictionary will be mutually exclusive for
    key > value (can't contain key with more than one value)."""


    # Updates merge_dict() with new matches for every position pair and for every match found at those positions.
    for position, duplicate_set in current_match_dict.items():

        # print(duplicate_list)
        duplicate_list = sorted(duplicate_set)
        lower_cluster_id = duplicate_list[0]

        # If multiple matches found on one position, takes one at the time for easier code structure
        for higher_cluster_id in duplicate_list[1:]:
            prev_value = None
            try:
                prev_value = merge_dict[lower_cluster_id]
            except KeyError:
                merge_dict[higher_cluster_id] = lower_cluster_id
            if not prev_value == None:
                if prev_value == lower_cluster_id:
                    pass
                elif prev_value < lower_cluster_id:
                    merge_dict[higher_cluster_id] = prev_value
                    merge_dict[lower_cluster_id] = prev_value
                else:
                    del merge_dict[higher_cluster_id]
                    merge_dict[higher_cluster_id] = lower_cluster_id
                    merge_dict[prev_value] = lower_cluster_id

    return merge_dict

class ClusterObject(object):
    """ Cluster object"""

    def __init__(self, clusterId):

        self.barcode_to_bc_dict = dict()
        self.Id = int(clusterId.split()[1]) # Remove 'Cluster' string and \n from end

    def addRead(self, line):

        accession = line.split()[2].rstrip('.')
        barcode = accession.split(':')[-1]
        self.barcode_to_bc_dict[barcode] = self.Id # Extract header and remove '...'

class readArgs(object):
    """ Reads arguments and handles basic error handling like python version control etc."""

    def __init__(self):
        """ Main funcion for overview of what is run. """

        readArgs.parse(self)
        readArgs.pythonVersion(self)

    def parse(self):

        #
        # Imports & globals
        #
        import argparse, multiprocessing
        global args

        parser = argparse.ArgumentParser(description=__doc__)

        # Arguments
        parser.add_argument("input_tagged_bam", help=".bam file tagged with @RG tags and duplicates marked (not taking "
                                                     "cluster id into account).")
        parser.add_argument("output_bam", help=".bam file without cluster duplicates")

        # Options
        parser.add_argument("-F", "--force_run", action="store_true", help="Run analysis even if not running python 3. "
                                                                           "Not recommended due to different function "
                                                                           "names in python 2 and 3.")
        parser.add_argument("-p", "--processors", type=int, default=multiprocessing.cpu_count(),
                            help="Thread analysis in p number of processors. Example: python "
                                 "TagGD_prep.py -p 2 insert_r1.fq unique.fa")

        args = parser.parse_args()

    def pythonVersion(self):
        """ Makes sure the user is running python 3."""

        #
        # Version control
        #
        import sys
        if sys.version_info.major == 3:
            pass
        else:
            sys.stderr.write('\nWARNING: you are running python ' + str(
                sys.version_info.major) + ', this script is written for python 3.')
            if not args.force_run:
                sys.stderr.write('\nAborting analysis. Use -F (--Force) to run anyway.\n')
                sys.exit()
            else:
                sys.stderr.write('\nForcing run. This might yield inaccurate results.\n')

    def processors(self):

        #
        # Processors
        #
        import multiprocessing
        processor_count = args.processors
        max_processor_count = multiprocessing.cpu_count()
        if processor_count == max_processor_count:
            pass
        elif processor_count > max_processor_count:
            sys.stderr.write(
                'Computer does not have ' + str(processor_count) + ' processors, running with default (' + str(
                    max_processor_count) + ')\n')
            processor_count = max_processor_count
        else:
            sys.stderr.write('Running with ' + str(processor_count) + ' processors.\n')

        return processor_count

class Summary(object):
    """ Summarizes chunks"""

    def __init__(self):

        self.totalReadPairsCount = int()
        self.totalReadPairsMarkedAsDuplicates = int()
        self.duplicatePositionWithoutProximity = int()# Duplicates without proximity to other duplicates (=> cannot be cluster duplicate)

        self.readPairsMerged = int() # Rather the count of reads that have changed cluster ID.

        self.ClustersRemovedDueToMerge = int()

        # self.totalClusterCount
        # self.totalClusterCountPostMerge

        self.mergeDict = str()
        self.log = args.output_bam + '.log'
        with open(self.log, 'w') as openout:
            pass

    def reportMergeDict(self, merge_dict):
        """ Saves a readable string format of merge_dict to write to out."""

        for high_clusterId, low_clusterId in merge_dict.items():
            self.mergeDict += str(high_clusterId) + '\t=>\t' + str(low_clusterId) + '\n'

    def writeLog(self):

        import time
        with open(self.log, 'a') as openout:
            openout.write(time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + '\n')
            for objectVariable, value in vars(self).items():
                print('\n'+objectVariable)
                print(value)
                #print(self.attributes)

if __name__=="__main__": main()