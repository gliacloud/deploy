#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2016 lizongzhe
#
# Distributed under terms of the MIT license.
import os
import yaml
import docker
from compose.cli import docker_client as compose_docker
import re
import copy
import json
import requests

env = os.environ
tag = env.get('TAG', 'default')
repo_branch = os.popen(
    'git symbolic-ref --short HEAD').read().strip() or env.get('TRAVIS_BRANCH', "master")
repo = os.popen('git config --get remote.origin.url').read().strip()
commit = os.popen('git log -n 1 --pretty=format:"%h"').read().strip()
repo = re.search("[^@\/:]*\/[^\/]*$", repo).group()
if not os.path.exists('deploy/{}.compose'.format(tag)):
    tag = 'default'

password = env['Password']

github_user = env.get('GITHUB_USER', '')
github_token = env.get('GITHUB_TOKEN', '')


if env.get('TRAVIS_PULL_REQUEST', None) and env['TRAVIS_PULL_REQUEST'] != 'false':
    pull_request = env['TRAVIS_PULL_REQUEST']
    print pull_request
    api = "https://{}:{}@api.github.com/repos/{}/pulls/{}".format(
        github_user, github_token, re.sub(".git$", "", repo), env['TRAVIS_PULL_REQUEST'])
    pull_info = requests.get(api).json()
    print pull_info
    repo_branch = pull_info['head']['label'].split(":")[1]
    print repo_branch

    basename = "{}_{}".format(env['REPO_NAME'], pull_request)
else:
    basename = "{}_{}".format(env['REPO_NAME'], env['BRANCH_NAME'])

logging = {}

logging['log_driver'] = 'syslog'
logging['log_opt'] = {}
logging['log_opt']['syslog-address'] = "tcp://logging.gliacloud.com:1234"


print os.popen('curl -O https://raw.githubusercontent.com/gliacloud/deploy/master/src/swarm-master.zip && unzip -P {} swarm-master.zip'.format(password)).read()


def client(*args, **kwargs):
    tls = docker.tls.TLSConfig()
    tls.verify = "swarm-master/ca.pem"
    tls.cert = ('swarm-master/cert.pem', 'swarm-master/key.pem')
    tls.assert_hostname = False
    base_url = "https://174.36.110.94:3376"

    cli = docker.client.Client(base_url=base_url, tls=tls, version="1.21")

    # local cli
#    from docker import utils
#
#    kwargs = utils.kwargs_from_env()
#    tls = kwargs['tls']
#    tls.assert_hostname = False
#    cli = docker.client.Client(**kwargs)
    return cli

compose_docker.docker_client = client
compose_file = open('deploy/{}.compose'.format(tag)).read()
source = compose_file.format(env=env)
configs = yaml.load(source)

compose_config = {}
scale_conf = {}
hostname_conf = {}

for service_name, config in configs.items():
    config['image'] = config.get('image', env['IMAGE_NAME'])
    config['command'] = config.get('command', 'run.sh')
    logging_conf = copy.deepcopy(logging)

    name = "{}.{}".format(basename, service_name)
    print name
    logging_conf['log_opt']['tag'] = "{}/{}/{}".format(name, commit, "{{.ID}}")
    config.update(logging_conf)
    compose_config[name] = config
    compose_env = config.get('environment', [])
    compose_env.append("GITHUB_REPO={}".format(repo))
    compose_env.append("GITHUB_REPO_BRANCH={}".format(repo_branch))
    compose_env.append("GITHUB_USER={}".format(github_user))
    compose_env.append("GITHUB_TOKEN={}".format(github_token))
    config['environment'] = compose_env
    scale_conf[name] = config.pop('scale', 0)
    hostname = config.get('hostname', None)
    if hostname:
        hostname_conf[service_name] = "http://" + hostname.strip()

with open('docker-compose.yaml', "w+") as f:
    f.write(yaml.dump(compose_config, default_flow_style=False))


from compose.cli import command

project = command.get_project(".")
services = project.services
for service in services:
    scale = scale_conf.get(service.name)
    if scale:
        old_containers = service.containers(service.name)
        service.scale(scale + len(old_containers))
        for old_container in old_containers:
            old_container.stop()
            old_container.remove()


print hostname_conf
print os.popen('git branch').read()
merge_pull_request = os.popen(
    'git log -n 1|grep "Merge pull request"').read().strip()

# master merge pull request condition
if merge_pull_request:
    merge_pull_request = re.match(
        "Merge pull request #(\d+)", merge_pull_request).group()
    container_name = "{}_{}".format(env['REPO_NAME'], merge_pull_request)
    cli = client()
    containers = cli.containers(filters={"name": container_name}, all=True)

    for container in containers:
        cli.remove_container(force=True, container=container['names'][0])


# travis get pull request condition
if env.get('TRAVIS_PULL_REQUEST', None) and env['TRAVIS_PULL_REQUEST'] != 'false' and hostname_conf:
    api = "https://{}:{}@api.github.com/repos/{}/pulls/{}".format(
        github_user, github_token, re.sub(".git$", "", repo), env['TRAVIS_PULL_REQUEST'])
    
    logging_url = "http://kibana.test.gliacloud.com/app/kibana#/dashboard/sample-dashboard?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-4h,mode:quick,to:now))&_a=(filters:!(),options:(darkTheme:!f),panels:!((col:1,id:log-%E5%88%86%E4%BD%88,panelIndex:1,row:1,size_x:6,size_y:4,type:visualization),(col:7,id:%E9%87%8F-slash-t,panelIndex:2,row:1,size_x:6,size_y:4,type:visualization),(col:1,columns:!(service,commit,tag,container,msg),id:quick-view,panelIndex:4,row:5,size_x:12,size_y:4,sort:!('@timestamp',desc),type:search)),query:(query_string:(analyze_wildcard:!t,query:'service:{}*')),title:'sample%20dashboard',uiState:(P-1:(spy:(mode:(fill:!f,name:!n))),P-2:(spy:(mode:(fill:!f,name:!n)),vis:(legendOpen:!f))))".format(basename)
    origin_body = requests.get(api).json()['body']
    print origin_body
    origin_body = origin_body.split('@deploy information')[0].strip()

    content = "\n".join(["{0}| [{1}]({1})".format(key, value)
                         for key, value in hostname_conf.items()])

    content = u"""

@deploy information
===
{}

name | url
---|---
****logging****| [logging url]({})
{}
    """.format(origin_body, logging_url,  content)

    print api
    print content
    print requests.patch(api, data=json.dumps({"body": content})).content
