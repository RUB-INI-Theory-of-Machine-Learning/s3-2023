#!/bin/bash

# Get the number of folders in the 'out' directory
num=$(printf "%03d" $(ls out | wc -l))
echo $num

# Possible csearch and lsearch options
csearches=("beam"  "greedy" "heuristic" "grasp" "as" "mmas") # "grasp" "greedy" "heuristic" "as" "mmas")
# lsearches=("bi" "fi" "ils" "rls" "sa")
instances=("data/waste-collection/sample.txt" "data/waste-collection/input20.txt" "data/waste-collection/input50.txt" "data/waste-collection/input100.txt")

# Iterate over all input files in 'data/campus-network'
for file in ${instances[@]}; do
    # Extract the instance name from the file path, removing the last 4 characters (.txt)
    instance_name=$(basename "$file" .txt)

    # Iterate over all csearch options
    for csearch in ${csearches[@]}; do
        # Create output directory if it doesn't exist
        mkdir -p "out/$num/$instance_name"
        # Run the Python script with the current options and input file
        python3 src/base.py --log-level info --csearch "$csearch" --input-file "$file" --log-file "out/$num/$instance_name/log_$csearch.txt" > "out/$num/$instance_name/output_$csearch.txt"
    done

    # Iterate over all lsearch options
    for lsearch in ${lsearches[@]}; do
        # Create output directory if it doesn't exist
        mkdir -p "out/$num/$instance_name"
        # Run the Python script with the current options and input file
        python3 src/base.py --log-level info --lsearch "$lsearch" --input-file "$file" --log-file "out/$num/$instance_name/log_$lsearch.txt" > "out/$num/$instance_name/output_$lsearch.txt"
    done
done
