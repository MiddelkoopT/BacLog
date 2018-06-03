#!/bin/zsh

PYTHON=python

while /bin/true ; do 
 ((run+=1))
 sleep 1
 ${PYTHON} baclog.py >&! nohup.out.$run
done
