#!/usr/bin/env bash

if [ -z $TIMEOUT ]; then
  TIMEOUT=0;
fi

if [ -z $KILLOUT ]; then
  KILLOUT=0
fi
timeout -k${KILLOUT} ${TIMEOUT} /opt/qpme/SimQPN.sh -r batch "/tmp/experiment/in.qpe" >>/tmp/experiment/out.log
# echo "$?">>/tmp/experiment/out.log
