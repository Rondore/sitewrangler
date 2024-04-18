#!/usr/bin/env python3

import os
import re
import requests
import glob
import subprocess
from libsw import logger, version, builder, settings, file_filter

class CurlBuilder(builder.AbstractArchiveBuilder):
    """
    A class to build curl from source.
    """
    def __init__(self):
        super().__init__('curl')

    def get_installed_version(self):
        about_text = subprocess.getoutput('LD_LIBRARY_PATH="' + builder.ld_path + '" /usr/local/bin/curl -V')
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

def libs_path():
    path = settings.get('curl_libs')
    if path == 'unset':
        paths = builder.ld_path.split(':')
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
  Get the path the current curl source directory.
  """
  dirs = glob.glob('/usr/local/src/curl-*/')
  dir = False
  for d in dirs:
      if not dir:
          dir = d
      else:
          if os.path.getmtime(d) > os.path.getmtime(dir):
              dir = d
  return dir
