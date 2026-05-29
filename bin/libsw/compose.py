#!/usr/bin/env python3

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