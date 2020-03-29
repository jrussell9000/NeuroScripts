#!/usr/bin/env bash

parse_list=$(cat info.*.txt | grep -A3 "NODDI")
echo "$parse_list" | awk 'BEGIN {RS="--"} {print ($2" "$8)}' > seq_times.txt

while read -r line; do
    seq=$(echo $line | cut -f1 -d" ")
    time=$(echo $line | cut -f2 -d" " | cut -c-4)
    echo "$seq"
    echo "$time"
    for bvalfile in $(find $GRADINFO_PATH -name "*.bval" -printf '%P\n'); do
        if [[ "${bvalfile}" == *"${time}"* ]]; then
            mv "${bvalfile}" "${seq}".bval
        fi
    done
    for bvecfile in $(find $GRADINFO_PATH -name "*.bvec" -printf '%P\n'); do
        if [[ "${bvecfile}" == *"${time}"* ]]; then
            mv "${bvecfile}" "${seq}".bvec
        fi
    done
done < seq_times.txt

rm seq_times.txt