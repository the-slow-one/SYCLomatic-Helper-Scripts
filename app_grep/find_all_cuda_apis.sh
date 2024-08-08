#!/bin/bash

GREP_OPT_LIST_API="-ho"
GREP_OPT_LIST_FILE="-l"
GREP_OPT_ADD_LINE_NO="-n"

find $1 \
  '('\
    -name "*.cpp" \
    -o -name "*.cu" \
    -o -name "*.hpp" \
    -o -name "*.h" \
    -o -name "*.cuh" \
  ')' \
  -type f \
  -exec grep ${GREP_OPT_LIST_FILE} \
  -e "cu[A-Z][A-Za-z0-9]\+" \
  -e "cuda[A-Z][A-Za-z0-9]\+" \
  -e "nvrtc[A-Z][A-Za-z0-9]\+" \
  -e "__device__" \
  -e "__global__" \
  -e "threadIdx.[xyz]" \
  -e "blockDim.[xyz]" \
  -e "gridDim.[xyz]" \
  -e "thrust::" \
  -e "::thrust::" \
  -e "cub::" \
  -e "::cub::" \
  -e "cudnn" \
  -e "nccl" \
  -e "cublas" \
  -e "cufft" \
  -e "curand" \
  -e "cusolver" \
  -e "cusparse" \
  -e "vpi" \
  -e "nvjpeg" \
  -e "nvtiff" \
  -e "npp" \
  -e "cutensor" \
  -e "amgx" \
  -e "nvshmem" \
  {} +
