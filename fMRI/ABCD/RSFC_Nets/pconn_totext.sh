#!/usr/bin/env bash

# Takes as an argument a directory containing a collection of newly exported pconn cifti files
# Converts the values in the correlation matrices to Z-scores ('atanh')
# Exports the converted correlation matrices to CSV files

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PCONN_DIR=$1
PCONN_CIFTIS_RAW="${PCONN_DIR}/*.pconn.nii"
PCONN_CSV_DIR="${PCONN_DIR}/pconn_csv"

if [ -d "${PCONN_CSV_DIR}" ]; then
  rm -rf "${PCONN_CSV_DIR}"
fi

mkdir "${PCONN_CSV_DIR}"

for PCONN in ${PCONN_CIFTIS_RAW}; do
  PCONN_CSV_OUT="${PCONN_CSV_DIR}/$(basename ${PCONN}).csv"
  echo "${PCONN_CSV_OUT}"
  wb_command -cifti-convert -to-text ${PCONN} ${PCONN_CSV_OUT}
done
