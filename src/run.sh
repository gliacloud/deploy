#! /bin/bash
#
# run.sh
# Copyright (C) 2016 lizongzhe <lizongzhe@lizongzhedeMacBook-Pro.local>
#
# Distributed under terms of the MIT license.
#

set -e
cd /tmp
curl -s  https://raw.githubusercontent.com/gliacloud/deploy/master/src/git.zip > git.zip
unzip -P $Password git.zip 
mv git ~/.ssh 
git clone --depth=1 --branch=$BRANCH $REPO /work
cd /work 
git submodule init 
git submodule update
eval $CMD
