#! bin/bash

#
# Argument parsing
#

while getopts "he" OPTION; do
	case ${OPTION} in

	    e)
            echo 'picard_path=/external/picard-tools-2.5.0/picard.jar'
            echo 'bowtie2_reference=/references/Bowtie2Index/genome'
            exit 0
	        ;;

		h)
		    echo ''
			echo 'This script creates paths.txt containing the paths to external software used by the WGH pipeline'
			echo ""
			echo 'Useage: bash set_path.sh <picard_path> <Bowtie2_ref> <BLR_folder>'
			echo ''
			echo "Positional arguments (required)"
			echo "  <picard_path>       Path to picard tools jar file (e.g. /picard_2.5.0/picard.jar)"
			echo "  <Bowtie2_ref>       Path to bowtie2 reference (e.g. /Bowtie2Index/genome)"
			echo "  <BLR_path           Path to BLR folder (e.g. /GitHub_repos/BLR)"
			echo ""
			echo "Optional arguments"
			echo "  -h  help (this output)"
			echo "  -e  example structure of a correct paths.txt file"
			echo ''
			exit 0
			;;
	esac
done

#
# Positional redundancy for using options
#

ARG1=${@:$OPTIND:1}
ARG2=${@:$OPTIND+1:1}
ARG2=${@:$OPTIND+2:1}

if [ -z "$ARG1" ] || [ -z "$ARG2" ] || [ -z "$ARG3" ]
then
    echo ""
    echo "ARGUMENT ERROR"
    echo "Did not find all three positional arguments, see -h for more information."
    echo "(got picard_path:"$ARG1", Bowtie2_ref:"$ARG2" and BLR_folder:"$ARG3" instead)"
    echo ""
    exit 0
fi

#
# If relative path is used, converts to absolute
#

if [[ "$ARG1" != /* ]]
then
    echo 'set_paths: picard_path supplied as relative, writing as absolute'
    work_dir=$(pwd)
    ARG1=$work_dir'/'$ARG1

elif [[ "$ARG2" != /* ]]
then
    echo 'set_paths: bowtie2_ref supplied as relative, writing as absolute'
    work_dir=$(pwd)
    ARG2=$work_dir'/'$ARG2
fi

elif [[ "$ARG3" != /* ]]
then
    echo 'set_paths: BLR_folder supplied as relative, writing as absolute'
    work_dir=$(pwd)
    ARG3=$work_dir'/'$ARG3
fi

#
# Writing files
#

wgh_path=$(ARG3)
echo 'set_paths: Creating paths.txt in your WGH_Analysis folder'

printf 'picard_path='$ARG1 > $wgh_path/paths.txt
printf '\nbowtie2_reference='$ARG2 >> $wgh_path/paths.txt
printf '\nwgh_path='$ARG3 >> $wgh_path/paths.txt
