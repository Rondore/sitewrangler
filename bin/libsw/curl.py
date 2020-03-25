#!/usr/bin/env python3

import os
import re
import requests
import glob
import subprocess
from libsw import logger, version, builder, settings

class CurlBuilder(builder.AbstractArchiveBuilder):
    """
    A class to build curl from source.
    """
    def __init__(self):
        super().__init__('curl', build_dir="/opt/curl/")

    def get_installed_version(self):
        about_text = subprocess.getoutput('/usr/local/bin/curl -V')
        match = re.match(r'curl ([0-9\.]*)', about_text)
        if match == None:
            return '0'
        version = match.group(1)
        return version

    def get_updated_version(self):
        request = requests.get('https://curl.haxx.se/download.html')
        regex = re.compile(r'\.tar\.gz')
        link_line = False
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            link_line = line
            break
        if not link_line:
            return link_line
        return re.sub(r'.*href="/download/curl-([^"]*)\.tar\.gz".*', r'\1', link_line)

    def get_source_url(self):
        return 'https://curl.haxx.se/download/curl-' + self.source_version + '.tar.gz'

    def dependencies(self):
        return ['openssl']

    def install(self, log):
        super().install(log)
        deploy_environment(log)

def deploy_environment(log):
    """
    Configure the system linker to use the new copy of openssl if the setting
    'deploy_curl' is set to True.

    Args:
        log - An open log to write to
    """
    if settings.get_bool('deploy_curl'):
        filename = '/etc/ld.so.conf.d/curl.conf'
        log.log('Making sure ' + filename + ' exists')
        ld_filter = AppendUnique(filename, libs_path())
        ld_filter.run()
    subprocess.run(['ldconfig'])

def libs_path():
    path = settings.get('curl_libs')
    if path == 'unset':
        paths = ['/usr/local/lib', '/usr/local/lib64']
        at = -1
        while path == 'unset' or not os.path.exists(path + '/libcurl.so'):
            at += 1
            if at >= len(paths):
                return False
            path = paths[at]
        settings.set('curl_libs', path)
    return path

def get_curl_path():
  """
  Get the path the current curl binary directory.
  """
  dirs = glob.glob('/opt/curl/curl-*/')
  dir = False
  for d in dirs:
      if not dir:
          dir = d
      else:
          if os.path.getmtime(d) > os.path.getmtime(dir):
              dir = d
  return dir
