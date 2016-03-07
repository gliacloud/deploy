#!/usr/bin/env python
import os
import re
import urllib2
import zlib
import docker
from cStringIO import StringIO
import json
import os
import tempfile
import yaml
from compose.cli import docker_client as compose_docker
import pprint

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


def parser_vars():
    env = os.environ.copy()

    # build vars
    env['ENV_DOCKERFILE'] = os.path.join(
        CUR_PATH, env.get("ENV_DOCKERFILE", "env/Dockerfile"))
    env['ENV_BUILD_PATH'] = os.path.join(
        CUR_PATH, env.get("ENV_BUILD_PATH", "env"))

    # container vars
    env['BUILD_PATH'] = env.get("BUILD_PATH", ".")
    env["WORK_DIR"] = env.get("WORK_DIR", "src")

    env_file_pattern = os.path.join(env['ENV_BUILD_PATH'], "**")
    # default vars
    # os.popen('shasum `find {} -type f`|shasum'.format(env_file_pattern)).read().split()[0]
    env["ENV_HASH"] = "hash"
    env["REPO_URL"] = os.popen(
        'git config --get remote.origin.url').read().strip()
    env["BRANCH_NAME"] = env.get('TRAVIS_BRANCH', os.popen(
        'git symbolic-ref --short HEAD').read().strip())

    repo = re.search("[^:\/]*\/[^\/]*$", env["REPO_URL"]
                     ).group().replace("/", "_").replace('.git', '').lower()
    branch = re.sub("[^a-zA-Z0-9]+", "_", env["BRANCH_NAME"]).lower()
    env_hash = env["ENV_HASH"]

    env["COMPOSE_TEMPLATE"] = env.get("COMPOSE_TEMPLATE", "compose.template")
    env["SERVIVE_IMAGE"] = "{}_srv_{}".format(repo, branch)
    env["ENV_IMAGE"] = "{}_env_{}".format(repo, env_hash)

    return env


def make_swarm_env():
    env = parser_vars()
    os.popen(
        'curl -O https://raw.githubusercontent.com/gliacloud/deploy/master/src/swarm-master.zip && unzip -P {} swarm-master.zip'.format(env['Password']))


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


def make_env_image():
    env = parser_vars()
    cli = client()
    if cli.images(env["ENV_IMAGE"]):
        return
    flow = cli.build(path=env["ENV_BUILD_PATH"], dockerfile=env[
                     "ENV_DOCKERFILE"], tag=env["ENV_IMAGE"])
    for line in flow:
        print line.strip()


def make_service_image():
    # make_env_image() ## docker swarm can't build with local image

    env = parser_vars()
    cli = client()

#    if cli.images(env["SERVIVE_IMAGE"]):
#        return
#
#    dockerfile = '''
#    FROM {}
#    ADD {} /work
#    WORKDIR /work
#    '''.format(env["ENV_IMAGE"], env["WORK_DIR"])
#
#    with open(os.path.join(env['BUILD_PATH'], "Dockerfile"), 'w+') as f:
#        f.write(dockerfile)

    flow = cli.build(path=env["BUILD_PATH"], tag=env["SERVIVE_IMAGE"])
    print env["SERVIVE_IMAGE"]
    print cli.info()
    print cli.images()
    for line in flow:
        print line.strip()


def make_compose_file():
    env = parser_vars()
    template = open(env['COMPOSE_TEMPLATE'])
    target = open("docker-compose.yml", 'w+')

    scale_conf = {}
    service_configs = yaml.load(template.read().format(env=env))
    for service_name in service_configs.keys():
        service_configs[service_name]['build'] = "."
        service_scale = service_configs[service_name].pop('scale', 0)
        # make new name with service image
        new_name = "{}.{}".format(env['SERVIVE_IMAGE'], service_name)
        service_configs[new_name] = service_configs.pop(service_name)

        if service_scale:
            scale_conf[new_name] = service_scale

    target.write(yaml.dump(service_configs, default_flow_style=False))
    target.close()
    template.close()
    return scale_conf


def deploy_service():
    env = parser_vars()
    make_swarm_env()
    scale_conf = make_compose_file()
    print os.popen("cd swarm-master && source activite && cd .. && docker info").read()

    from compose.cli import command
    project = command.get_project(CUR_PATH)
    services = project.services
    project.stop()
    project.remove_stopped()
    for service in services:
        scale = scale_conf.get(service.name)
        if scale:
            service.scale(scale)

# replace compose docker client
compose_docker.docker_client = client

deploy_service()
