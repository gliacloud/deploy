#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2016 lizongzhe 
#
# Distributed under terms of the MIT license.
import os
import yaml
from compose.cli import docker_client as compose_docker

print os.popen('curl -O https://raw.githubusercontent.com/gliacloud/deploy/master/src/swarm-master.zip && unzip -P {} swarm-master.zip'.format(password)).read()

def client(*args, **kwargs):
    tls = docker.tls.TLSConfig()
    tls.verify = "swarm-master/ca.pem"
    tls.cert = ('swarm-master/cert.pem', 'swarm-master/key.pem')
    tls.assert_hostname = False
    base_url = "https://174.36.110.94:3376"

    cli = docker.client.Client(base_url=base_url, tls=tls)


    ## local cli
    from docker import utils
    
    kwargs = utils.kwargs_from_env()
    tls = kwargs['tls']
    tls.assert_hostname = False
    cli = docker.client.Client(**kwargs)
    return cli

compose_docker.docker_client = client


env = os.environ()
tag = env.get('TAG', 'default')
if os.path.exists('{}.compose'.format(tag)):
    tag = 'default'

compose_file = open('{}.compose'.format(tag))
source = compose_file.format(env=env).read()
configs = yaml.loads(source)

compose_config = {}
scale_conf = {}

basename = "{}_{}".format(env['REPO_NAME'], env['BRANCH_NAME'])

for service_name, config in configs.items():
    config['image'] = config.get('image', env['IMAGE_NAME'])
    config['command'] = config.get('command', 'curl -s run.sh|bash')

    name = "{}.{}".format(basename, service_name)
    compose_config[name] = config
    compose_env = compose_config.get('environment', [])
    compose_env.append("Password={}".format(password))
    scale_conf[name] = config.pop('scale', 0)

with open('docker-compose.yaml') as f:
    f.write(configs, default_flow_style=False)

password = env['Password']



from compose.cli import command

project = command.get_project(CUR_PATH)
services = project.services
project.stop()
project.remove_stopped()
for service in services:
    scale = scale_conf.get(service.name)
    if scale:
        service.scale(scale)

