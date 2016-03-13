#! /bin/bash
#
# run.sh
# Copyright (C) 2016 lizongzhe <lizongzhe@lizongzhedeMacBook-Pro.local>
#
# Distributed under terms of the MIT license.
#

set -e
git clone https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_REPO --branch=$REPO_BRANCH --depth=1 /work
cd /work 
git submodule init 
git submodule update
eval $CMD
