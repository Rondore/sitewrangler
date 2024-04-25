#!/usr/bin/env python3

import os
import tarfile
import requests
import datetime
import subprocess
import glob
import re
import shutil
import platform
from libsw import logger, version, email, settings, file_filter, system
from abc import ABC, abstractmethod

debug = True
ld_path = "/usr/local/lib64:/usr/local/lib:/usr/local/pgsql/lib:/usr/local/modsecurity/lib"
ld_flags = "-L/usr/local/lib64/ -L/usr/local/lib/ -L/usr/local/pgsql/lib -L/usr/local/modsecurity/lib"
cpp_flags = "-I/usr/local/include/ -I/usr/local/modsecurity/include -I/usr/local/pgsql/include"
pkg_config_path = "/usr/local/lib64/pkgconfig/:/usr/local/lib/pkgconfig/"
build_env = dict(os.environ, LD_LIBRARY_PATH=ld_path, LDFLAGS=ld_flags, CPPFLAGS=cpp_flags, PKG_CONFIG_PATH=pkg_config_path)
set_sh_ld = 'LD_LIBRARY_PATH=' + ld_path + ' '

def is_frozen(slug):
    """
    Returns True if the slug is set to be restricted from updating.
    """
    freeze_file = settings.get('install_path') + 'etc/build-freeze'
    if os.path.exists(freeze_file):
        with open(freeze_file) as frozen:
            for line in frozen:
                if slug == line.strip():
                    return True
    return False

def freeze(slug):
    """
    Prevent a builder from updating it's source code to a newer version.
    The software will still be re-built if it's dependants are upated.
    """
    freeze_file = settings.get('install_path') + 'etc/build-freeze'
    return file_filter.AppendUnique(freeze_file, slug).run()

def unfreeze(slug):
    """
    Allow a builder to update it's source code to a newer version. This
    will not start a build.
    """
    freeze_file = settings.get('install_path') + 'etc/build-freeze'
    return file_filter.RemoveExact(freeze_file, slug).run()

def list_frozen():
    frozen_list = []
    freeze_file = settings.get('install_path') + 'etc/build-freeze'
    with open(freeze_file) as frozen:
        for line in frozen:
            frozen_list.append(line.strip())
    return frozen_list

def populate_config_arg_file(file_path, config_array, log):
    if os.path.exists(file_path):
        with open(file_path) as args:
            log.log('Reading configuration from ' + file_path)
            for arg in args:
                arg = arg.strip()
                if len(arg) == 0:
                    continue
                if arg[0] == '!':
                    clean_arg = arg[1:]
                    if clean_arg in config_array:
                        config_array.remove(clean_arg)
                    else:
                        log.log('Unable to remove configure argument ' + clean_arg)
                else:
                    config_array.append(arg)
    return config_array

def populate_patch_file(file_path, patch_array, log):
    if os.path.exists(file_path):
        with open(file_path) as args:
            log.log('Reading patches from ' + file_path)
            for arg in args:
                arg = arg.strip()
                name, url = arg.split(maxsplit=1)
                if len(name) == 0:
                    continue
                if name[0] == '!':
                    clean_name = name[1:]
                    for pair in patch_array:
                        if pair[0] == clean_name:
                            patch_array.remove(pair)
                    else:
                        log.log('Unable to remove patch argument ' + clean_name)
                elif len(url) != 0:
                    patch_array.append([name, url])
    return patch_array

class AbstractBuilder(ABC):
    """
    An abstract class to build source packages downloaded from tar files.
    """
    def __init__(self, slug, build_dir="/usr/local/src/", source_version=False):
        self.slug = slug
        self.source_version = source_version
        self.build_dir = build_dir
        # a dynamic list of builder objects that are dependant upon this software
        # this shold only be populated by a BuildQueue or similar
        self.dependents = []

    @abstractmethod
    def get_source_url(self):
        """
        This method returns the download path for the software wich often
        includes the version number.
        """
        pass

    @abstractmethod
    def update_needed(self):
        """
        Checks to see if an update is needed and returns a boolean indicating if
        it does need an update.
        """
        pass

    @abstractmethod
    def version_reference(self):
        """
        A version number that can be compared to a remote build server.
        """
        pass

    @abstractmethod
    def cleanup_old_versions(self, log):
        """
        Remove build logs and source folders for older versions of the software
        build built.

        Args:
            log - An open log to write to.
        """
        pass

    def dependencies(self):
        """
        Returns a list of slugs of the other software this builder relies on.
        """
        return []

    def source_dir(self, version=False):
        """
        Returns the path of the source code directory following a download.

        Args:
            version - The software version to use for the source path
        """
        if version == False:
            version = self.source_version
        return self.build_dir + self.slug + '-' + version + '/'

    @abstractmethod
    def fetch_source(self, source, log):
        """
        Fetch the source code of the software and extracts it if needed.

        Args:
            source - The source URL
            log - An open log file or null
        """
        pass

    def get_patches(self, log):
        """
        Get an array of patches used to modify the source code prior to configure or make commands.
        The array is populated by two entry arrays structered like this:
        ['Patch-Name', 'https://example.com/patch']

        Args:
            log - An open log file
        """
        patch_array = []
        patch_directory = settings.get('install_path') + 'etc/build-patchs/' + self.slug
        patch_array = populate_patch_file(patch_directory, patch_array, log)
        patch_directory = settings.get('install_path') + 'etc/build-patches/user/' + self.slug
        patch_array = populate_patch_file(patch_directory, patch_array, log)
        return patch_array

    def apply_patches(self, log):
        """
        Apply patches to the source code prior to configure or make commands.

        Args:
            log - An open log file
        """
        patch_array = self.get_patches(log)
        local_dir = settings.get('install_path') + 'var/cache/patches/' + self.slug + '/'
        if len(patch_array) > 0 and not os.path.exists(local_dir):
            os.makedirs(local_dir)
        for name, url in patch_array:
            local_file = local_dir + name
            if not os.path.exists(local_file):
                response = requests.get(url)
                with open(local_file, "w") as f:
                    f.write(response.text)
            log.log('Applying patch ' + name)
            patch_command = ['patch', '-ruN', '-p1', '-d', self.source_dir(), '-i', local_file]
            retval = log.run(patch_command)
            log.log('Done applying patch ' + name)

    def get_config_arg_file(self):
        """
        Returns the name of the file that lists arguments that are passed to
        the configure command. When overridden, this method can return an array
        of filenames instead.
        """
        return settings.get('install_path') + 'etc/build-config/' + self.slug

    def get_user_config_arg_file(self):
        """
        Returns the name of the file that lists arguments that are passed to
        the configure command. When overridden, this method can return an array
        of filenames instead.
        """
        return settings.get('install_path') + 'etc/build-config/user/' + self.slug

    def populate_config_args(self, log, command=False):
        """
        Populates a configure command with it's proper arguments from the
        matching configuration file.

        Args:
            command - A default configure command array
        """
        if command == False:
            command=['./configure']
        command = self.populate_hard_config_args(log, command)
        command = self.populate_user_config_args(log, command)
        return command

    def populate_hard_config_args(self, log, config_array):
        """
        Populates a configure command with it's proper arguments from the
        matching configuration file provided by Site Wrangler.

        Args:
            command - A default configure command array
        """
        log.log('Fetching provided config arguments')
        file_path_list = self.get_config_arg_file()
        if type(file_path_list) is str:
            file_path_list = [file_path_list]
        for file_path in file_path_list:
            config_array = populate_config_arg_file(file_path, config_array, log)
        return config_array

    def populate_user_config_args(self, log, config_array):
        """
        Populates a configure command with it's proper arguments from the
        matching configuration file provided by the system adminstrator.

        Args:
            command - A default configure command array
        """
        log.log('Fetching user config arguments')
        file_path_list = self.get_user_config_arg_file()
        if type(file_path_list) is str:
            file_path_list = [file_path_list]
        for file_path in file_path_list:
            config_array = populate_config_arg_file(file_path, config_array, log)
        return config_array

    def install(self, log):
        """
        Install the software to the system.

        Args:
            log - An open log file or null
        """
        old_pwd = os.getcwd()
        target_dir = self.source_dir()
        if os.path.exists(target_dir):
            os.chdir(target_dir)
            log.run(['make', 'install'], env=build_env)
            if not settings.get_bool('build_server'):
                self.clean(log)
        os.chdir(old_pwd)

    def make_args(self):
        return []

    def make(self, log):
        """
        Build the software.

        Args:
            log - An open log file or null
        """
        retval = False
        old_pwd = os.getcwd()
        target_dir = self.source_dir()
        if os.path.exists(target_dir):
            os.chdir(target_dir)
            #TODO add nice -19
            make = ['make', '-l', settings.get('max_build_load')]
            make.extend(self.make_args())
            retval = log.run(make, env=build_env)
        os.chdir(old_pwd)
        return retval

    def log_name(self):
        name = settings.get('install_path') + 'var/log/build/' + self.slug + '.log'
        return name

    def deploy_log_name(self, remote_address):
        name = settings.get('install_path') + 'var/log/deploy/' + self.slug + '-' + remote_address + '.log'
        return name

    def run_pre_config(self, log):
        """
        This function gets called after the source code is download but before
        it is configured. It is often used to run bash scripts that generate the
        configure file.

        Args:
            log - An open log file or null
        """
        pass

    def clean(self, log):
        """
        Clean build binaries for the software.

        Args:
            log - An open log file or null
        """
        old_pwd = os.getcwd()
        target_dir = self.source_dir()
        if os.path.exists(target_dir):
            os.chdir(target_dir)
            log.run(['make', 'clean', '-l', settings.get('max_build_load')], env=build_env)
        os.chdir(old_pwd)

    def check_build(self):
        """
        Since some source code is not compiled on it's own, this method runs an
        extra check to make sure the sofware was fetched correctly.
        """
        return True

    def build(self):
        """
        Download or update the source code, compile it and then install it.
        """
        logfile = self.log_name()
        success = False
        old_pwd = os.getcwd()
        logdir = os.path.dirname(logfile)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        with open(logfile, 'w+') as open_log:
            log = logger.Log(open_log)
            log.log("Build started for " + self.slug + " at " + str(datetime.datetime.now()))
            if is_frozen(self.slug):
                log.log("Note: Running rebuild of frozen package")
            source_url = self.get_source_url()
            if not is_frozen(self.slug):
                log.log('Fetching ' + source_url)
                self.fetch_source(source_url, log)
                self.apply_patches(log)
            os.chdir(self.source_dir())
            log.log("Running pre-config")
            self.run_pre_config(log)
            log.log("Getting config arguments")
            command = self.populate_config_args(log)
            config_ret_val = 0
            if len(command) > 0:
                log.log("Running configuration")
                if debug:
                    log.log('CONFIG: ' + ' '.join(command))
                config_ret_val = log.run(command, env=build_env)
            log.log("Running make")
            if config_ret_val != 0:
                log.log(self.slug + ' configure command failed. (exit code ' + str(config_ret_val) + ') Exiting.')
            else:
                make_ret_val = self.make(log)
                if make_ret_val != 0: # if not success
                    log.log(self.slug + ' make command failed. (exit code ' + str(make_ret_val) + ') Exiting.')
                else:
                    log.log("Installing")
                    self.install(log)
                    log.log("Build completed for " + self.slug + " at " + str(datetime.datetime.now()))
                    success = self.check_build()
                    self.cleanup_old_versions(log)

        os.chdir(old_pwd)
        if not success:
            email.send_admin_logfile('Build failed for  ' + self.slug, logfile)
        elif settings.get_bool('email_admin_on_build_success'):
            email.send_admin_log_clip('Build succeeded for ' + self.slug, logfile)
        return success, logfile

    def update_if_needed(self):
        """Check for updates and then run build() if needed."""
        if self.update_needed():
            return self.build()
        return False, False

    def deploy(self, remote_address, log):
        """
        Push a built package from a buid server to a production server.
        """
        log.log('Starting remote install of ' + self.slug + ' to ' + remote_address)
        dir = self.source_dir()
        if dir[-1:] != '/':
            dir += '/'
        subprocess.getoutput('ssh root@' + remote_address + ' -t "mkdir -p \'' + dir + '\'"')
        subprocess.getoutput("rsync -a --delete '" + dir + "' root@'" + remote_address + "':'" + dir + "'")
        subprocess.getoutput('ssh root@' + remote_address + ' -t "sw build installprebuilt ' + self.slug + '" + "' + self.source_version + '"')
        log.log('Completed remote install of ' + self.slug + ' to ' + remote_address)
        #TODO return success
        return True

    def needs_deploy(self, remote_address, log, force=False):
        """
        Check if a package needs to be pushed from a buid server to a production server.
        """
        if force:
            return True
            # Force can be ignored in overriding implementations.  This is the case with PHP as
            # the version of PHP may not be enabled on the target server.
        local_ver = str(self.version_reference()).strip()
        remote_ver = subprocess.getoutput('ssh root@' + remote_address + ' -t "sw build version ' + self.slug + '" 2>/dev/null').strip()
        # print('L: "' + local_ver + '", R: "' + remote_ver + '"')
        return local_ver != remote_ver


def find_old_build_elements(pre_ver_text, post_ver_text):
    """
    Locate build directories or log files from outdated versions.
    """
    elements = []
    name = pre_ver_text + '*' + post_ver_text
    current = False
    current_version = False
    print('looking for old build files: ' + name)
    for entry in glob.glob(name):
        skip_chars = len(pre_ver_text)
        post_skip = 0 - len(post_ver_text)
        this_version = entry[skip_chars:post_skip]
        if not current:
            current = entry
            current_version = this_version
        else:
            if version.first_is_higher(this_version, current_version):
                elements.append(current)
                current = entry
                current_version = this_version
            else:
                elements.append(entry)
    return elements

class AbstractArchiveBuilder(AbstractBuilder):
    """Abstract class to build source packages downloaded from tar files."""

    @abstractmethod
    def get_installed_version(self):
        """
        Get the version of the software installed on the system or the number 0
        if missing.
        """
        pass

    def version_reference(self):
        return self.get_installed_version()

    @abstractmethod
    def get_updated_version(self):
        """
        Get the current up-to-date (stable) release version for the software.
        """
        pass

    def updated_version_reference(self):
        if is_frozen(self.slug):
            return self.version_reference()
        return self.get_updated_version()

    def cleanup_old_versions(self, log):
        """
        Remove old old build directories and log files.

        Args:
            log - An open log file or null
        """
        found = False
        found_version = False
        for log_file in find_old_build_elements(settings.get('install_path') + 'var/log/build/' + self.slug + '-', '.log'):
            os.remove(log_file)
            log.log("Removed old log file " + log_file)
        search = self.source_dir('VERSION')
        position = search.find('VERSION')
        search = search[:position]
        for folder in find_old_build_elements(search, '/'):
            shutil.rmtree(folder)
            log.log("Removed old source directory " + folder)

    def update_needed(self):
        if is_frozen(self.slug):
            return False
        old = self.get_installed_version()
        if old == False or len(old) == 0:
            return True
        new = self.updated_version_reference()
        return version.first_is_higher(new, old)

    def log_name(self):
        if not self.source_version:
            self.source_version = self.updated_version_reference()
        name = settings.get('install_path') + 'var/log/build/' + self.slug
        if self.source_version and len(self.source_version) > 0:
            name += '-' + self.source_version
        name += '.log'
        return name

    def fetch_source(self, source, log):
        """
        Fetch the source tar file and extract it
        """
        ext = ''
        type = ''
        if source [-7:] == '.tar.gz':
            ext = '.tar.gz'
            type = 'r:gz'
        elif source [-8:] == '.tar.bz2':
            ext = '.tar.bz2'
            type = 'r:bz2'
        elif source [-4:] == '.tgz':
            ext = '.tgz'
            type = 'r:gz'
        tarname = self.build_dir + self.slug + '-' + self.source_version + ext
        if not os.path.exists(self.build_dir):
            os.mkdir(self.build_dir)
        response = requests.get(source)
        with open(tarname, "wb") as f:
            f.write(response.content)
        print('')
        with tarfile.open(tarname, type) as tar:
            tar.extractall(self.build_dir)
        os.remove(tarname)
        #print(tarname)

    def build(self):
        if not self.source_version:
            self.source_version = self.updated_version_reference()
        return super().build()

class AbstractGitBuilder(AbstractBuilder):
    "Abstract class to build source packages."
    def __init__(self, slug, build_dir="/usr/local/src/", source_version=False, branch='master'):
        self.branch = branch
        super().__init__(slug, build_dir, source_version)

    def cleanup_old_versions(self, log):
        pass

    def update_needed(self):
        if is_frozen(self.slug):
            return False
        if not os.path.exists(self.source_dir()):
            return True
        old_pwd = os.getcwd()
        os.chdir(self.source_dir())
        output = subprocess.getoutput("git remote show origin | grep '(up to date)'")
        up_to_date = len(output) > 0
        os.chdir(old_pwd)
        return not up_to_date

    def version_reference(self):
        #TODO get a version number from the installed program instead of the source code
        bash = 'date -d "$(git -C "' + self.source_dir() + '" log -1 | grep -i "date" | head -1 | awk \'{print $2" "$3" "$4" "$6" "$5$7}\')" +%s'
        commit_date = subprocess.getoutput(bash)
        return commit_date

    def source_dir(self):
        return self.build_dir + self.slug + '/'

    def get_clone_args(self):
        return []

    def git_init(self, log=False):
        """
        Initialize the local copy of the git repository.

        Args:
            log (optional) - a Logger object to run commands through
        """
        old_pwd = os.getcwd()
        os.chdir(self.build_dir)
        run_command = ['git', 'clone', self.get_source_url()]
        run_command.extend(self.get_clone_args())
        run_command.extend(['--branch', self.branch])
        if log == False:
            subprocess.run(run_command)
        else:
            log.run(run_command)
        os.chdir(old_pwd)

    def fetch_source(self, source, log):
        old_pwd = os.getcwd()
        target_dir = self.source_dir()
        if os.path.exists(target_dir):
            os.chdir(target_dir)
            self.clean(log)
            log.run(['git', 'pull', 'origin', self.branch])
        else:
            self.git_init(log)
        os.chdir(old_pwd)

    # def fetch_source(self, source, log):
    #     old_pwd = os.getcwd()
    #     target_dir = self.source_dir()
    #     if os.path.exists(target_dir):
    #         os.chdir(target_dir)
    #         self.clean(log)
    #         log.run(['git', 'pull', 'origin', self.branch])
    #     else:
    #         os.chdir(self.build_dir)
    #         log.run(['git', 'clone', self.get_source_url(), '--branch', self.branch])
    #         #os.chdir(target_dir)
    #     os.chdir(old_pwd)

    def build(self):
        success, logfile = super().build()
        if success:
            success = self.check_build()
        return success, logfile

def builder_array_contains_slug(array, slug):
    for builder in array:
        if builder.slug == slug:
            return True
    return False

def get_systemd_config_path():
    possibilities = [
        '/lib/systemd/system/',
        '/etc/systemd/system/'
    ]
    for path in possibilities:
        if os.path.isdir(path):
            return path
    return possibilities[0]