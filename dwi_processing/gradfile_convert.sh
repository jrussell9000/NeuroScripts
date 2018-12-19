#!/usr/bin/env bash

printf "\\nConverting raw gradient files..."

  #--UNPACKING the tar file to a temporary directory
    tmp_dir
    graddir_tmp="${TMP}"

    tar xf "${GRADPACK}" -C "${graddir_tmp}"
    if [[ $? != 0 ]]; then
      printf "\\nERROR: Could not unpack the gradient tar file - %s" "${GRADPACK}"
      exit 1
    fi
  
  #--TRIMMING the names of each file in the unpacked directory to "mmhhyy.{bval/bvec}""

  #---Locating the info file
      info_file=$(find "${INPUT_DIR}" -name "info*.txt" -printf '%P\n' | head -n 1)
      if [ -z "${info_file}" ]; then
        printf "\\nERROR: Scan info file (info.XXXXXX.txt) not found in gradient files path."
        exit 1
      else
        printf "\\nFound scan info file in gradient files path."
      fi

  #---Deleting unnecessary files, trimming the names of those we want to keep, and copying them to the raw_dir  
      printf "\\nRenaming and reformatting raw diffusion gradient files from the scanner..."
      for file in "${graddir_tmp}"/Research*.txt; do
        if [[ $file == *bvals2* || $file == *orientations2* || $file == *diff_amp* ]]; then
          rm "${file}"
        fi
        if [[ $file == *bvals_* ]]; then
          fname=$(basename "${file%.*}" | cut -c32- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
          mv "${file}" "${graddir_tmp}"/"${fname}".bval
        elif [[ $file == *orientations_* ]]; then
          fname=$(basename "${file%.*}" | cut -c39- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
          mv "${file}" "${graddir_tmp}"/"${fname}".bvec
        fi
      done

  #---Parsing the info file and getting any lines containing "NODDI" and the three below them 
  #---then echo each pair of SeriesDescription and AcquisitionTime values to a file, 'seq_times.txt'
      parse_list=$(grep -A3 "NODDI" "${INPUT_DIR}"/"${info_file}")
      echo "$parse_list" | awk 'BEGIN {RS="--"} {print ($2" "$8)}' > "${graddir_tmp}"/seq_times.txt

  #---For each line of 'seq_times.txt', save the first field as variable $seq, 
  #---and the second field as variable $time (without the seconds, which don't always match)
      while read -r line; do
        seq=$(echo "${line}" | cut -f1 -d" ")
        time=$(echo "${line}" | cut -f2 -d" " | cut -c-4)
        #----For each bval file, if the file name matches the $time variable, rename it as the $seq variable
        for bvalfile in "${graddir_tmp}"/*.bval; do
          if [[ "${bvalfile}" == *"${time}"* ]]; then
              mv "${bvalfile}" "${graddir_tmp}"/"${seq}".bval
          fi
        done
        #----For each bvec file, if the file name matches the $time variable, rename it as the $seq variable
        for bvecfile in "${graddir_tmp}"/*.bvec; do 
          if [[ "${bvecfile}" == *"${time}"* ]]; then
              mv "${bvecfile}" "${graddir_tmp}"/"${seq}".bvec
          fi
        done
      done < "${graddir_tmp}"/seq_times.txt

  #--REFORMATTING each file to the FSL scheme...

  #---For each .bvec file, get the number of columns in the file, then loop across them starting with the third (the first two are just labels)
  #---For each column in the loop, cut it, remove the last entry (extra line of zeros), echo it to transpose from a column to a row and append it to a temp file
  #---When the loop is over, replace the original .bvec file with the newly formatted temp file
      for bvecfile in "${graddir_tmp}"/*.bvec; do
        numc=$(($(head -n 1 "$bvecfile" | grep -o " " | wc -l) + 1))
        for ((i=3;i<="$numc";i++)); do 
          TEMP=$(cut -d" " -f"$i" "$bvecfile")
          TEMP=$(awk '{$NF=""}1' <(echo ${TEMP} )) #Do NOT double quote
          echo "${TEMP}" >> temp.txt
        done
        mv temp.txt "${bvecfile}"
        cp "${bvecfile}" "${preproc_dir}"
      done

  #---For each .bval file, grab the third column (first two are just labels), remove the last row (extra line of zeros)
  #---Echo it to tranpose from a column to a row, then export it to a temp file.  Rename the temp file with the original bval
      for bvalfile in "${graddir_tmp}"/*.bval; do
        TEMP=$(cut -d" " -f"3" "$bvalfile")
        TEMP=$(awk -F" " '{NF--; print}' <(echo ${TEMP} )) #Do NOT double quote
        echo "${TEMP}" > temp.txt
        mv temp.txt "${bvalfile}"
        cp "${bvalfile}" "${preproc_dir}"
      done
  else #If we don't need to convert the raw scan
    cp "${STUDY_DIR}"/diff_files/"${PostAnt}".b* "${STUDY_DIR}"/diff_files/"${AntPost}".b* "${preproc_dir}"
  fi #----END raw gradient files conversion