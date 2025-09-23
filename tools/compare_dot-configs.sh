#!/bin/bash

# Compare dot-config files (new vs. existing in wrs_tn2_configuration)
# Used to evaluate the differences between directly generated (by wrs-config-generator) and
# converted (generated single file and converted to each HW version)

DOTCONF_FILE_PREFIX="dot-config"
DOTCONF_FILE_NAMES=("production" "unilac")

SORTED_FILE_PREFIX="sorted"
DIFF_FILE_PREFIX="diff"

# Determine the project root folder
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"    # get the directory of the running script
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"                             # project root is parent of script dir

# Define target folders
GEN_DIR="$PROJECT_ROOT/output/config"
TN2_DIR="$PROJECT_ROOT/wrs_tn2_configuration/dot-configs/8.x"

# Strings given below appear in new dot-config and expected
expected_strings=("DOTCONF_HW_VERSION" \
                    "Build-time configuration" \
                    "CONFIG_DOTCONF_INFO" \
                    "CONFIG_DOTCONF_LOCAL_OVERWRITE" \
                    "LLDPD_TX_INTERVAL" \
                    "IFACE_DOWN_AFTER_BOOT" \
                    "CONFIG_SNMP_SYSTEM_CLOCK_MONITOR_ENABLED" \
                    "CONFIG_SPLL_HPLL" \
                    "CONFIG_SPLL_MPLL" \
                    "CONFIG_SPLL_REVERSE_OVERWRITE" \
                    "CONFIG_TOD_SOURCE_IRIGB" \
                    "CONFIG_TOD_SOURCE_NMEA" \
                    "CONFIG_TOD_SOURCE_NONE" \
                    "External source of Time of Day at boot" \
                    "Overwrite SoftPLL Settings")

# Generated files are sorted to normalized text files.
# $ sort -u file1 > sorted_file1

# Then they are compared with existing files and the result is stored.
# $ diff -y --suppress-common-lines -I "CONFIG_TO_IGNORE" sorted_file1 sorted_file2 > cmp_file1

# Finally look for any configuration option other than expected options

# Build sorted files in a given directory
build_sorted_files() {
    # $1 - directory

    file_paths=()
    for file_name in ${DOTCONF_FILE_NAMES[@]}; do
        file_paths+=($1/${DOTCONF_FILE_PREFIX}_${file_name}*) # pattern match
    done

    # sort existing files
    for file_path in ${file_paths[@]}; do
        if [ -f $file_path ]; then
            file_name=${file_path##$1/}  # get the filename only
            sort -u $file_path > $1/${SORTED_FILE_PREFIX}_${file_name}
        fi
    done

    # show all sorted files
    #ls -l $1/${SORTED_FILE_PREFIX}*
}

# Compare sorted files in given directories
compare_sorted_files() {
    # $1, $2 - directories

    opts="-y --suppress-common-lines -I DOTCONF_INFO -I ROOT_PWD_CYPHER"

    file_paths=()
    for file_name in ${DOTCONF_FILE_NAMES[@]}; do
        file_paths+=($1/${SORTED_FILE_PREFIX}*) # pattern match
    done

    # compare existing files
    for file_path in ${file_paths[@]}; do
        if [ -f $file_path ]; then
            file_name=${file_path##$1/${SORTED_FILE_PREFIX}_}  # get the filename only

            # compare if another file exists
            another_file_path=$2/${SORTED_FILE_PREFIX}_${file_name}
            #echo "$file_path vs. $another_file_path"

            if [ -f $another_file_path ]; then
                #echo "=> $1/${DIFF_FILE_PREFIX}_${file_name}"
                diff $opts $file_path $another_file_path > $1/${DIFF_FILE_PREFIX}_${file_name}
            fi
        fi
    done

    # show all files with comparison results
    ls -l $1/${DIFF_FILE_PREFIX}*
}

# Look for any configuration option other than expected options
parse_comparison_result() {
    # $1 - directory, where comparison results are stored

    # get files (file paths) with comparison results
    file_paths=($1/${DIFF_FILE_PREFIX}*)

    # parse comparison result to look for any extra line
    for file_path in ${file_paths[@]}; do
        if [ -f $file_path ]; then
            extra_lines=()

            # parse each line
            while IFS= read -r line; do
                is_string_found=""

                # check if line has an expected string
                for string in ${expected_strings[@]}; do
                    if [[ "$line" == *"$string"* ]]; then
                        is_string_found=$string
                        break # break for loop
                    fi
                done

                # if line has extra string, then collect it
                if [ "$is_string_found" = "" ]; then
                    extra_lines+=($line)
                fi
            done < "$file_path"

            # print extra lines, if any found
            if [ ${#extra_lines[@]} -ne 0 ]; then
                echo "$file_path:"
                echo "   ${extra_lines[@]}"
            fi
        fi
    done
}

# Remove files according to prefix in a given directory
remove_files() {
    # $1 - directory
    # $2 - prefix

    # remove files
    rm $1/${2}*
}

build_sorted_files $GEN_DIR
build_sorted_files $TN2_DIR

compare_sorted_files $GEN_DIR $TN2_DIR

remove_files $GEN_DIR $SORTED_FILE_PREFIX
remove_files $TN2_DIR $SORTED_FILE_PREFIX

parse_comparison_result $GEN_DIR
