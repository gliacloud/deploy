#! /bin/bash
#
# build.sh
# Copyright (C) 2016 lizongzhe <lizongzhe@lizongzhedeMacBook-Pro.local>
#
# source build.sh deploy 
#

if [ -z $TRAVIS_BRANCH ]; 
then
    export BRANCH_NAME=`git symbolic-ref --short HEAD`
else
    export BRANCH_NAME=$TRAVIS_BRANCH
fi

export REPO_NAME=`git config --get remote.origin.url|sed "s/^https:\/\/github.com\///" | sed "s/git@github.com://" | sed "s/.git$//" | sed "s/[^a-zA-Z0-9]/_/g"| tr '[A-Z]' '[a-z]'`
export IMAGE_HASH=$(shasum `find image/* -type f` | shasum | awk '{print $1}')
export IMAGE_NAME=gliacloud/$REPO_NAME:$IMAGE_HASH

if [[ `docker images -q $IMAGE_NAME|wc -l|awk '{print $1}'` == 0 ]]
then
    echo "start pull $IMAGE_NAME"
    if [[ `docker pull $IMAGE_NAME` ]]
    then
        echo "start build $IMAGE_NAME"
        docker build -t $IMAGE_NAME image
        
        if [[ $DOCKERHUB_USER != ''  ]]
        then
            docker login --username=$DOCKERHUB_USER --password=$DOCKERHUB_PASSWORD --email=$DOCKERHUB_EMAIL
            docker push $IMAGE_NAME
        fi
    fi
fi

echo "build image $IMAGE_NAME success"

