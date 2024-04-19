#!/usr/bin/env python3

import os, subprocess
from libsw import builder, version

class ImageMagickBuilder(builder.AbstractGitBuilder):
    def __init__(self, build_dir="/usr/local/src/", source_version=False):
        super().__init__('image-magick', build_dir, source_version, branch="main")

    def get_source_url(self):
        return 'https://github.com/ImageMagick/ImageMagick.git'

    def source_dir(self):
        return self.build_dir + 'ImageMagick/'

    def install(self, log):
        super().install(log)
        log.run('ldconfig')

    def update_needed(self):
        if builder.is_frozen(self.slug):
            return False
        if not os.path.exists(self.source_dir()):
            return True
        latest = self._get_latest_tag()
        current = self.version_reference()
        return not latest == current

    def _get_latest_tag(self):
        old_pwd = os.getcwd()
        source_dir = self.source_dir()
        if not os.path.exists(source_dir):
            self.git_init()
        os.chdir(source_dir)
        subprocess.getoutput('git fetch origin')
        output = subprocess.getoutput("git tag")
        latest_ver = '0'
        latest_patch = 0
        for line in output.split('\n'):
            if line == 'master' or line == 'continuous':
                continue
            subline = line.split('-')
            if len(subline) != 2:
                continue
            line_ver = subline[0]
            line_patch = int(subline[1])
            if version.first_is_higher(line_ver, latest_ver) or (line_ver == latest_ver and line_patch > latest_patch):
                latest_ver = line_ver;
                latest_patch = line_patch;
        os.chdir(old_pwd)
        if latest_ver == '0' and latest_patch == 0:
            return ''
        return latest_ver + '-' + str(latest_patch)

    def version_reference(self):
        return subprocess.getoutput(builder.set_sh_ld + '/usr/local/bin/magick --version | grep "^Version" | sed "s~.*ImageMagick\s\+\([0-9\\.\\-]\\+\\)\\s\\+.*~\\1~"')

    def fetch_source(self, source, log):
        self.branch = self._get_latest_tag()
        return super().fetch_source(source, log)

    def git_init(self, log=False):
        super().git_init(log)
        old_pwd = os.getcwd()
        os.chdir(self.source_dir())
        tag = self._get_latest_tag()
        print('Hard resetting to latest tag: ' + tag)
        run_command = ['git', 'reset', '--hard', tag]
        if log == False:
            subprocess.run(run_command)
        else:
            log.run(run_command)
        os.chdir(old_pwd)
