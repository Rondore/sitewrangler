#!/usr/bin/env python3

import subprocess
import os
from libsw import settings, template

def compose_dir() -> str:
    return settings.get('install_path') + 'etc/container-compose/'

def template_dir() -> str:
    return settings.get('install_path') + 'etc/compose-templates/'

def write_compose(filename: str):
    source_file = template_dir() + filename
    target_file = compose_dir() + filename
    template_vars = template.get_template_vars()
    template.write_template_with_variables(source_file, target_file, template_vars)

def get_compose_file_args(compose_file: str | False = False):
    compose_list = []
    parent_dir = compose_dir()
    if(compose_file):
        compose_list = ['-f', compose_file]
    else:
        for file in os.listdir(parent_dir):
            extention = file.lower().split('.')[-1]
            if extention in ['yaml', 'yml']:
                compose_list.extend(['-f', parent_dir + file])
    return compose_list

def compose_up(compose_file: str | False = False):
    command: list[str] = [settings.get('build_system')]
    command.extend(['compose', 'up', '-d'])
    command.extend(get_compose_file_args(compose_file))
    output = subprocess.getoutput(command)
    return output

def compose_down(compose_file: str | False = False):
    command: list[str] = [settings.get('build_system')]
    command.extend(['compose', 'down'])
    command.extend(get_compose_file_args(compose_file))
    output = subprocess.getoutput(command)
    return output