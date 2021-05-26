#!/usr/bin/env bash

# Takes as an argument a directory containing a collection of newly exported pconn cifti files
# Converts the values in the correlation matrices to Z-scores ('atanh')
# Exports the converted correlation matrices to CSV files

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PCONN_DIR=$1
PCONN_CIFTIS_RAW="${PCONN_DIR}/*.pconn.nii"
PCONN_Z_DIR="${PCONN_DIR}/pconn_z"
PCONN_CIFTIS_Z="${PCONN_Z_DIR}/*.Z.pconn.nii"
PCONN_CSV_DIR="${PCONN_DIR}/pconn_csv"

if [ -d "${PCONN_Z_DIR}" ]; then
  rm -rf "${PCONN_Z_DIR}"
fi

mkdir "${PCONN_Z_DIR}"

for PCONN_RAW in ${PCONN_CIFTIS_RAW}; do
  PCONN_Z_OUT="${PCONN_Z_DIR}/$(basename ${PCONN_RAW%%pconn.nii})Z.pconn.nii"
  echo "${PCONN_Z_OUT}"
  wb_command -cifti-math "atanh(x)" ${PCONN_Z_OUT} -var x ${PCONN_RAW}
done

if [ -d "${PCONN_CSV_DIR}" ]; then
  rm -rf "${PCONN_CSV_DIR}"
fi

mkdir "${PCONN_CSV_DIR}"

for PCONN_Z in ${PCONN_CIFTIS_Z}; do
  PCONN_CSV_OUT="${PCONN_CSV_DIR}/$(basename ${PCONN_Z}).csv"
  echo "${PCONN_CSV_OUT}"
  wb_command -cifti-convert -to-text ${PCONN_Z} ${PCONN_CSV_OUT}
done
