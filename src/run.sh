#! /bin/bash
#
# run.sh
# Copyright (C) 2016 lizongzhe <lizongzhe@lizongzhedeMacBook-Pro.local>
#
# Distributed under terms of the MIT license.
#



wget https://raw.githubusercontent.com/gliacloud/deploy/master/src/git.zip 
unzip -P $Password git.zip 
mv git ~/.ssh 
git clone $REPO /work 
cd /work 
git submodule init 
git submodule update
eval $COMMAND
