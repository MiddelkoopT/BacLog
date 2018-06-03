#!/bin/bash

PYTHON=python

install -d log
while sleep 1 ; do 
  ((run+=1))
  ${PYTHON} baclog.py &> log/baclog.${run}.log
done
