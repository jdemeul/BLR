#! /usr/bin python3

def main():
    """Takes a fastq file barcode sequences in the header and writes a barcode fasta file with only unique entries. """

    #
    # Imports & globals
    #
    global args, summaryInstance, output_tagged_bamfile
    import BLR_functions as BLR, sys, pysam

    #
    # Argument parsing
    #
    argumentsInstance = readArgs()

    # Check python3 is being run
    if not BLR.pythonVersion(args.force_run): sys.exit()

    #
    # Data processing & writing output
    #

    # Generate dict with bc => bc_cluster consensus sequence
    BLR.report_progress("Starting analysis")
    clstr_generator = BLR.FileReader(args.input_clstr)
    cluster_dict = ProcessClusters(clstr_generator.fileReader())
    clstr_generator.close()

    # Read bam files and translate bc seq to BC cluster ID + write to out
    progress = BLR.ProgressReporter('Reads processed', 1000000)
    infile = pysam.AlignmentFile(args.input_mapped_bam, 'rb')
    out = pysam.AlignmentFile(args.output_tagged_bam, 'wb', template=infile)
    reads_with_non_clustered_bc = int()
    for read in infile.fetch(until_eof=True):
        read_bc = read.query_name.split()[0].split('_')[-1]

        # Fetch barcode cluster ID based on barcode sequence
        if not read_bc in cluster_dict:
            reads_with_non_clustered_bc += 1
        else:
            bc_id = cluster_dict[read_bc]
            read.set_tag('BC', str(bc_id), value_type='Z')  # Stores as string, makes duplicate removal possible. Can do it as integer as well.
            read.query_name = (read.query_name + '_BC:Z:' + str(bc_id))

        out.write(read)
        progress.update()

    infile.close()
    out.close()
    BLR.report_progress('Finished')

def ProcessClusters(openInfile):
    """
    Builds bc => bc_cluster dict (bc_cluster is given as the consensus sequence).
    """

    # For first loop
    if args.skip_nonclust: seqs_in_cluster = 2

    # Reads cluster file and saves as dict
    cluster_dict = dict()
    cluster_ID = int()
    for line in openInfile:

        # Reports cluster to master dict and start new cluster instance
        if line.startswith('>'):

            # If non-clustered sequences are to be omitted, removes if only one sequence makes out the cluster
            if args.skip_nonclust and seqs_in_cluster < 2:
                del cluster_dict[current_key]
            seqs_in_cluster = 0

            cluster_ID += 1
            current_value = cluster_ID
        else:
            current_key = line.split()[2].lstrip('>').rstrip('...').split(':')[2]
            cluster_dict[current_key] = current_value
            seqs_in_cluster +=1

    return(cluster_dict)

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
        import argparse
        global args

        parser = argparse.ArgumentParser(description="Tags bam files with barcode clustering information. Looks for raw "
                                                     "sequence in read header and puts barcode cluster ID in BC tag as "
                                                     "well as in header.")

        # Arguments
        parser.add_argument("input_mapped_bam", help=".bam file with mapped reads which is to be tagged with barcode id:s.")
        parser.add_argument("input_clstr", help=".clstr file from cdhit clustering.")
        parser.add_argument("output_tagged_bam", help=".bam file with barcode cluster id in the bc tag.")

        # Options
        parser.add_argument("-F", "--force_run", action="store_true", help="Run analysis even if not running python 3. "
                                                                           "Not recommended due to different function "
                                                                           "names in python 2 and 3.")
        parser.add_argument("-s", "--skip_nonclust", action="store_true", help="Does not give cluster ID:s to clusters "
                                                                               "made out by only one sequence.")

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

if __name__=="__main__": main()
