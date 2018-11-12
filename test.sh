while read -r subjects; do
	subj_array+=("$subjects")
done <subj_list.txt
list=$(IFS=,; echo "${subj_array[*]}")
ls ~/proc/( $list )
# printf -v var "${subj_array[*]}"
