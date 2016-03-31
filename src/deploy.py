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

env = os.environ
tag = env.get('TAG', 'default')
repo_branch = os.popen('git symbolic-ref --short HEAD').read().strip() or env.get('TRAVIS_BRANCH', "master")
repo = os.popen('git config --get remote.origin.url').read().strip()
repo = re.search("[^@\/:]*\/[^\/]*$", repo).group()
if not os.path.exists('deploy/{}.compose'.format(tag)):
    tag = 'default'

password = env['Password']
basename = "{}_{}".format(env['REPO_NAME'], env['BRANCH_NAME'])

github_user = env.get('GITHUB_USER', '')
github_token = env.get('GITHUB_TOKEN', '')



logging = {}
logging['driver'] = 'syslog'
logging['options'] = {}
logging['options']['syslog-address'] = "tcp://logging.gliacloud.com:1234"
logging['options']['syslog-facility'] = "deamon"
logging['options']['syslog-tls-skip-verify'] = "true"
logging['options']['tag'] = basename


print os.popen('curl -O https://raw.githubusercontent.com/gliacloud/deploy/master/src/swarm-master.zip && unzip -P {} swarm-master.zip'.format(password)).read()

def client(*args, **kwargs):
    tls = docker.tls.TLSConfig()
    tls.verify = "swarm-master/ca.pem"
    tls.cert = ('swarm-master/cert.pem', 'swarm-master/key.pem')
    tls.assert_hostname = False
    base_url = "https://174.36.110.94:3376"

    cli = docker.client.Client(base_url=base_url, tls=tls)

#    ## local cli
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

for service_name, config in configs.items():
    config['image'] = config.get('image', env['IMAGE_NAME'])
    config['command'] = config.get('command', 'run.sh')
    config['logging'] = logging

    name = "{}.{}".format(basename, service_name)
    compose_config[name] = config
    compose_env = config.get('environment', [])
    compose_env.append("GITHUB_REPO={}".format(repo))
    compose_env.append("GITHUB_REPO_BRANCH={}".format(repo_branch))
    compose_env.append("GITHUB_USER={}".format(github_user))
    compose_env.append("GITHUB_TOKEN={}".format(github_token))
    config['environment'] = compose_env
    scale_conf[name] = config.pop('scale', 0)

with open('docker-compose.yaml', "w+") as f:
    f.write(yaml.dump(compose_config, default_flow_style=False))


from compose.cli import command

project = command.get_project(".")
services = project.services
project.stop()
project.remove_stopped()
for service in services:
    scale = scale_conf.get(service.name)
    if scale:
        service.scale(scale)

