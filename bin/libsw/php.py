#!/usr/bin/env python3

import inquirer
import glob
import os
import subprocess
import re
import requests
import shutil
import pwd
import time
from shutil import copyfile
from libsw import logger, file_filter, version, builder, settings, service, system, user, input_util

# enable_legacy_versions = settings.get_bool('enable_php_legacy_versions')
php80version = '8.0.30' # 04 Aug 2023
php74version = '7.4.33' # 28 Nov 2022
php73version = '7.3.33' # 19 Nov 2021
php72version = '7.2.34' # 01 Oct 2020
php71version = '7.1.33' # 18 Dec 2019
php70version = '7.0.33' # 10 Jan 2019
php56version = '5.6.40' # 10 Jan 2019

legacy_versions = [
    php80version,
    php74version,
    php73version,
    php72version,
    php71version,
    php70version,
    php56version
]

# enable_super_legacy_versions = settings.get_bool('enable_php_super_legacy_versions')
php55version = '5.5.38' # 21 Jul 2016
php54version = '5.4.45' # 03 Sep 2015
php53version = '5.3.29' # 14 Aug 2014
php52version = '5.2.17' # 06 January 2011
php51version = '5.1.6' # 24 Aug 2006
php50version = '5.0.5' # 05 Sep 2005
php44version = '4.4.9' # 07 Aug 2008
php43version = '4.3.11' # 31 Mar 2005
php42version = '4.2.3' # 6 Sep 2002
php41version = '4.1.2' # 12 March 2002
php40version = '4.0.6' # 23 June 2001
php30version = '3.0.18' # 20 Oct 2000

super_legacy_versions = [
    php55version,
    php54version,
    php53version,
    php52version,
    php51version,
    php50version,
    php44version,
    php43version,
    php42version,
    php41version,
    php40version,
    php30version
]

build_path = settings.get('build_path')

def php_build_path(sub_version):
    return build_path + 'php-' + sub_version  + '/'

def php_binary_path(sub_version):
    return build_path + 'php-' + sub_version  + '/bin/php'

def vhost_path(sub_version):
    return php_build_path(sub_version) + 'etc/php-fpm.d/'

def get_lib_path(sub_version):
    dir = subprocess.getoutput(php_binary_path(sub_version)+ '-config --ini-path')
    return dir + '/'

def restart_service(version, log=logger.Log(False)):
    """
    Restart a given PHP service.

    Args:
        version - The PHP subversion to start (such as 7.3)
        log (optional) - An open log file to log to
    """
    service.restart('php-' + version + '-fpm', log)

def get_installed_version(sub_version):
    """
    Get the full version installed for a given subversion.

    Args:
        sub_version - The first two numbers in a PHP version
    """
    return subprocess.getoutput(builder.set_sh_ld + php_binary_path(sub_version) + " -v 2>/dev/null | grep '^PHP " + sub_version + "' | awk '{print $2}'")

def get_versions(excluded_array=False):
    """
    Get an array of installed PHP versions.

    Args:
        excluded_array - (optional) An array of PHP versions to exclude from the array
    """
    from libsw import build_index
    if excluded_array == False:
        excluded_array=[]
    save_file = settings.get('install_path') + 'etc/enabled-packages'
    slugs = file_filter.get_trimmed_file_as_array(save_file)
    versions = []
    if slugs != False:
        for slug in slugs:
            if slug[:4] == 'php-':
                ver = slug[4:]
                versions.append(ver)
    return versions

def select_version(excluded_array=False):
    """
    Have the user select a PHP subversion, optionally excluding certain
    subversions.

    Args:
        excluded_array - (optional) A list of PHP subversions to exclude
    """
    if excluded_array == False:
        excluded_array=[]
    versions = get_versions(excluded_array)
    questions = [
        inquirer.List('ver',
                    message="Select PHP Version",
                    choices=versions
                )
    ]
    return inquirer.prompt(questions)['ver']

version_cache = False
def select_updated_version():
    """
    Prompt the user to select a PHP version from those avaliable at php.net.
    """
    global version_cache
    if not version_cache:
        versions = get_updated_versions()
        questions = [
            inquirer.List('ver',
                        message="Select PHP Version",
                        choices=versions
                    )
        ]
        version_cache = inquirer.prompt(questions)['ver']
    return version_cache

def get_enabled_vhost_path(version, username):
    """
    Get the path for an enabled PHP vhost file regardless of wether or not it exists.

    Args:
        version - The PHP version used in the file path
        username - The system user used in the file path
    """
    return vhost_path(version) + username + '.conf'

def get_disabled_vhost_path(version, username):
    """
    Get the path for a disabled PHP vhost file regardless of wether or not it exists.

    Args:
        version - The PHP version used in the file path
        username - The system user used in the file path
    """
    return vhost_path(version) + username + '.conf.disabled'

def get_vhost_path(version, user):
    """
    Get the path of the vhost file associated with a system user. If no vhost file is
    found the enabled path is returned.

    Args:
        version - The PHP version used in the file path
        user - The system user associated with the vhost file
    """
    enabled_path = get_enabled_vhost_path(version, user)
    disabled_path = get_disabled_vhost_path(version, user)
    if not os.path.exists(enabled_path) and os.path.exists(disabled_path):
        return disabled_path
    return enabled_path

def make_vhost(username, php_version):
    """
    Create a new PHP vhost file and restart the appropriate PHP service.

    Args:
        username - The system user who's home directory stores site files
        php_version - The PHP version to use
    """
    with open(settings.get('install_path') + 'etc/php-fpm-site', 'r') as template:
        vhost_file_path = get_enabled_vhost_path(php_version, username)
        vhost_dir = os.path.dirname(vhost_file_path)
        group = user.get_user_group(username)
        if not os.path.exists(vhost_dir):
            os.makedirs(vhost_dir)
        with open(vhost_file_path, 'w') as host:
            for line in template:
                line = line.replace('USERNAME', username, 10000)
                line = line.replace('GROUPNAME', group, 10000)
                host.write(line)
    add_logrotate_file(username)
    print('Created ' + vhost_file_path)
    restart_service(php_version)
    set_sys_user_version(username, php_version)

def enable_vhost(username):
    """
    Remove the suffix ".disabled" from a vhost file and restart the appropriate
    PHP service, thereby enabling the site/file.

    Args:
        username - The system user to enable
    """
    php_version = get_sys_user_version(username)
    if php_version == False:
        return False
    source = get_disabled_vhost_path(php_version, username)
    target = source[:-9] # to trim off '.disabled'
    os.rename(source, target)
    restart_service(php_version)
    return True

def disable_vhost(username):
    """
    Append the suffix ".disabled" to a vhost file and restart the appropriate
    PHP service, thereby disabling the site/file.

    Args:
        username - The system user to disable
    """
    php_version = get_sys_user_version(username)
    if php_version == False:
        return False
    source = get_enabled_vhost_path(php_version, username)
    target = source + '.disabled'
    os.rename(source, target)
    restart_service(php_version)
    return True

def remove_vhost(username):
    """
    Delete the PHP vhost file associated with a user and then restart the
    appropriate PHP service.

    Args:
        username - Delete the file associated with this system user
    """
    php_version = get_sys_user_version(username)
    if php_version == False:
        return False
    enabled_path = get_enabled_vhost_path(php_version, username)
    disabled_path = get_disabled_vhost_path(php_version, username)
    removed = False
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
        removed = True
    if os.path.exists(disabled_path):
        os.remove(disabled_path)
        removed = True
    if removed:
        restart_service(php_version)
    remove_logrotate_file(username)
    return removed

def edit_vhost(username):
    """
    Allow the user to edit a vhost file with the system text edior, restart the
    appropriate PHP service if modified.

    Args:
        username - The username associated with the PHP vhost file
    """
    php_version = get_sys_user_version(username)
    if php_version == False:
        return False
    path = get_vhost_path(php_version, username)
    if input_util.edit_file(path):
        print('Restarting php-' + php_version + '-fpm to apply changes.')
        restart_service(php_version)

def get_sys_user_version(username):
    """
    Get the PHP version currently in use for a given site.

    Args:
        username - The system user used in finding the PHP version
    """
    avaliable_versions = get_versions()
    # Search for enabled configuration files
    for ver in avaliable_versions:
        if os.path.exists(vhost_path(ver) + username + '.conf'):
            return ver
    # Search for disabled configuration files
    for ver in avaliable_versions:
        if os.path.exists(vhost_path(ver) + username + '.conf.disabled'):
            return ver
    return False


def set_sys_user_version(username, version):
    """
    Modify a system user's path so that a specific version of php is used by
    default for that user.

    Args:
        username - The username of the system user
        version - The PHP version to use
    """
    user_info = pwd.getpwnam(username)
    os.setegid(user_info.pw_gid)
    os.seteuid(user_info.pw_uid)
    try:
        target = user.home_dir(username) + '.bashrc'
        new_content = ''
        file_filter.UpdateSection(
                target,
                '# START PHP VERSION PATH',
                '# END PHP VERSION PATH',
                'export PATH=' + php_build_path(version) + 'bin' + os.pathsep + '$PATH\n' +
                'alias php=\'LD_LIBRARY_PATH="' + build_path + 'lib64:' + build_path + 'lib" php\'\n' +
                'alias wp=\'LD_LIBRARY_PATH="' + build_path + 'lib64:' + build_path + 'lib" php ' + build_path + 'wp-cli/wp-cli.phar\'\n'
            ).run()
        link_dir = '/home/' + username + '/.local/bin/'
        link_path = link_dir + 'php'
        if os.path.exists(link_path):
            os.unlink(link_path)
        if not os.path.exists(link_dir):
            os.makedirs(link_dir)
        os.symlink(php_binary_path(version), link_path)
    finally:
        os.setegid(0)
        os.seteuid(0)

def get_conf_files():
    """
    Get an array of all enabled configuration files.

    Return:
        An array of dictionaries with the keys: version, file, fullPath
    """
    avaliable_versions = get_versions()
    sites = []
    for ver in avaliable_versions:
        vpath = vhost_path(ver)
        for file in glob.glob(vpath + '*.conf'):
            sites.append( {"version": ver, "file": file[len(vpath):-5], "fullPath": file} )
    sites = sorted(sites, key=lambda k: k['file'])
    return sites

def get_disabled_conf_files():
    """
    Get an array of all disabled configuration files.

    Return:
        An array of dictionaries with the keys: version, file, fullPath
    """
    avaliable_versions = get_versions()
    sites = []
    for ver in avaliable_versions:
        vpath = vhost_path(ver)
        for file in glob.glob(vpath + '*.conf.disabled'):
            sites.append( {"version": ver, "file": file[len(vpath):-14], "fullPath": file} )
    sites = sorted(sites, key=lambda k: k['file'])
    return sites

def select_conf(query_message):
    """
    Prompt the user to select an enabled PHP configuration file.

    Args:
        query_message - The message to display to the user in the prompt
    """
    sites = get_conf_files()
    display_sites = []
    for site in sites:
        display_sites.append('(' + site['version'] + ') ' + site['file'])
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=display_sites
                )
    ]
    conf_file_text = inquirer.prompt(questions)['f']
    return sites[display_sites.index(conf_file_text)]

def select_disabled_conf(query_message):
    """
    Prompt the user to select a disabled PHP configuration file.

    Args:
        query_message - The message to display to the user in the prompt
    """
    sites = get_disabled_conf_files()
    display_sites = []
    for site in sites:
        display_sites.append('(' + site['version'] + ') ' + site['file'])
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=display_sites
                )
    ]
    conf_file_text = inquirer.prompt(questions)['f']
    return sites[display_sites.index(conf_file_text)]

def change_version(username, old_version, new_version):
    """
    Change the PHP version used for a given system user.

    Args:
        username - The system user of the site to change
        old_version - The current PHP version
        new_version - The PHP version to change the site to
    """
    vhost_directory = vhost_path(new_version)
    if not os.path.exists(vhost_directory):
        os.makedirs(vhost_directory)
    os.rename(vhost_path(old_version) + username + '.conf', vhost_directory + username + '.conf')
    set_sys_user_version(username, new_version)

    print('Restarting PHP...')
    restart_service(old_version)
    restart_service(new_version)
    print('Done')

def get_prerelease_user(force_refresh=False):
    """
    Get the php.net username associated with the latest prerelease version

    Args:
        force_refresh - (optional) When set to True, do not use cached values
    """
    cache_dir = settings.get('install_path') + 'var/cache/'
    cache_file = cache_dir + 'php-prerelease-user'
    use_cache = force_refresh == False
    prerelease_user = '';

    if os.path.exists(cache_file):
        max_age = settings.get_num('build_cache_age')
        mod_time = os.stat(cache_file).st_mtime
        age = time.time() - mod_time
        if age > max_age:
            use_cache = False
    else:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        use_cache = False

    if use_cache:
        file_array = file_filter.get_trimmed_file_as_array(cache_file)
        if len(file_array) > 0:
            return file_array[0]
        else:
            return ''
    else:
        request = requests.get('https://www.php.net/')
        regex = re.compile(r'.*"https://downloads\.php\.net/~([a-zA-Z0-9]*)/".*')
        for line in request.text.splitlines():
            match = regex.match(line)
            if match == None:
                continue
            match = match.group(1)
            if len(match) > 0:
                prerelease_user = match
                break
        with open(cache_file, 'w+') as cache_write:
            cache_write.write(prerelease_user + "\n")
        return prerelease_user

def get_updated_versions(force_refresh=False):
    """
    Get the full version numbers of versions avaliable at php.net.

    Args:
        force_refresh - (optional) When set to True, do not use cached values
    """
    vers = []
    cache_dir = settings.get('install_path') + 'var/cache/'
    cache_file = cache_dir + 'php-versions'
    use_cache = force_refresh == False

    if os.path.exists(cache_file):
        max_age = settings.get_num('build_cache_age')
        mod_time = os.stat(cache_file).st_mtime
        age = time.time() - mod_time
        if age > max_age:
            use_cache = False
    else:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        use_cache = False

    if use_cache:
        cached_versions = file_filter.get_trimmed_file_as_array(cache_file)
        if settings.get_bool('enable_php_prerelease_version'):
            return cached_versions
        else:
            clean_versions = []
            regex = re.compile(r'^[0-9\.]*$')
            for version in cached_versions:
                if regex.match(version):
                    clean_versions.append(version)
            return clean_versions
    else:
        request = requests.get('https://www.php.net/downloads.php')
        regex = re.compile(r'.*/distributions/php-([0-9\.]*)\.tar\.bz2.*')
        for line in request.text.splitlines():
            match = regex.match(line)
            if match == None:
                continue
            match = match.group(1)
            if len(match) > 0:
                vers.append(match)

        use_legacy = settings.get_bool('enable_php_legacy_versions')
        installed_versions = get_versions()
        if use_legacy:
            vers.extend(legacy_versions)
        else:
            for legacy in legacy_versions:
                sub_version = legacy[:legacy.find('.', legacy.find('.')+1)]
                if sub_version in installed_versions:
                    vers.append(legacy)

        use_super_legacy = settings.get_bool('enable_php_super_legacy_versions')
        if use_super_legacy:
            vers.extend(super_legacy_versions)
        else:
            for legacy in super_legacy_versions:
                sub_version = legacy[:legacy.find('.', legacy.find('.')+1)]
                if sub_version in installed_versions:
                    vers.append(legacy)

        if settings.get_bool('enable_php_prerelease_version'):
            vers.extend(get_prerelease_version(vers))
        with open(cache_file, 'w+') as cache_write:
            for v in vers:
                cache_write.write(v + "\n")
        return vers

def get_prerelease_version(version_array):
    request = requests.get('https://downloads.php.net/~' + get_prerelease_user(True) + '/')
    regex = re.compile(r'.*<a href="php-([0-9\.]*)([a-zA-Z]*)([0-9]+)\.tar\.bz2">.*')
    latest = False
    for line in request.text.splitlines():
        match = regex.match(line)
        if match == None:
            continue
        main_version = match.group(1)
        letter = match.group(2)[0]
        release_number = match.group(3)
        if len(main_version) > 0:
            combined = main_version + '.' + letter + '.' + release_number
            if not latest or version.first_is_higher(combined.lower(), latest.lower()):
                latest = combined
    if latest:
        version_array.append(latest)
    return version_array


class AddPid(file_filter.FileFilter):
    """Append a line to a PHP vhost file to have PHP create a pid file."""
    def filter_stream(self, in_stream, out_stream):
        search = re.compile(r'^(\s*;?\s*)(pid = run/php-fpm\.pid.*)')
        add_line = True
        for line in in_stream:
            line, count = search.subn('\2', line)
            if count > 0:
                add_line = False
            out_stream.write(line)
        if add_line:
            out_stream.write('pid = run/php-fpm.pid\n')
        return add_line

def deploy_environment(versions, log):
    """
    Install a PHP systemd init file if needed, then start the appropriate PHP
    version.

    Args:
        version - The PHP version to setup
        log - An open log to write to
    """
    bin_path = build_path + 'bin/php-' + versions['sub']
    base_path = php_build_path(versions['sub'])
    src_dir = versions['full']
    if '.a.' in src_dir:
        src_dir = src_dir.replace('.a.', 'alpha')
    if '.b.' in src_dir:
        src_dir = src_dir.replace('.b.', 'beta')
    if '.r.' in src_dir:
        src_dir = src_dir.replace('.r.', 'rc')
    if '.R.' in src_dir:
        src_dir = src_dir.replace('.R.', 'RC')
    src_dir = build_path + 'src/php-' + src_dir + '/'
    bin_link_exists = os.path.islink(bin_path) or os.path.isfile(bin_path)
    if not bin_link_exists:
        os.symlink(php_binary_path(versions['sub']), bin_path)
    lib_dir = get_lib_path(versions['sub'])
    copyfile(src_dir + 'php.ini-production', lib_dir + 'php.ini')

    fpm_conf_name = base_path + 'etc/php-fpm.conf'
    copyfile(fpm_conf_name + '.default', fpm_conf_name)
    file_filter.ReplaceRegex(fpm_conf_name, re.compile('^;?pid\s+='), 'pid = run/php-fpm.pid\n', 1).run()
    include_line = 'include=' + vhost_path(versions['sub']) + '*.conf'
    file_filter.AppendUnique(fpm_conf_name, include_line, True).run()

    AddPid(fpm_conf_name).run()

    write_primary_logrotate()

    systemd_file = builder.get_systemd_config_path() + 'php-' + versions['sub'] + '-fpm.service'

    if os.path.isfile(systemd_file):
        restart_service(versions['sub'], log)
    else:
        with open(systemd_file, 'w+') as unit_file:
            unit_file.write('[Unit]\n')
            unit_file.write('Description=The PHP ' + versions['sub'] + ' FastCGI Process Manager\n')
            unit_file.write('After=network.target\n')
            unit_file.write('\n')
            unit_file.write('[Service]\n')
            unit_file.write('Type=simple\n')
            unit_file.write('PIDFile=' + base_path + 'var/run/php-fpm.pid\n')
            unit_file.write('ExecStart=' + base_path + 'sbin/php-fpm --nodaemonize --fpm-config ' + base_path + 'etc/php-fpm.conf\n')
            unit_file.write('ExecReload=/bin/kill -USR2 $MAINPID\n')
            unit_file.write('Restart=always\n')
            unit_file.write('RestartSec=3\n')
            unit_file.write('Environment="LD_LIBRARY_PATH=' + builder.ld_path + '"\n')
            unit_file.write('\n')
            unit_file.write('[Install]\n')
            unit_file.write('WantedBy=multi-user.target\n')

        service.reload_init(log)
        service.enable('php-' + versions['sub'] + '-fpm', log)
        service.start('php-' + versions['sub'] + '-fpm', log)

        from libsw import firewall
        firewall.writepignore()
        if os.path.exists('/usr/sbin/lfd'):
            log.run('lfd', '-r')

def remove_environment(subversion, log):
    """
    Remove a version of PHP from the system.

    Args:
        subversion - The first two numbers in the PHP version
    """
    fullversion = get_installed_version(subversion)
    service.stop('php-' + subversion + '-fpm')
    log.log('Stopped php-' + subversion + '-fpm')
    service.disable('php-' + subversion + '-fpm')
    log.log('php-' + subversion + '-fpm disabled')
    binfile = build_path + 'bin/php-' + subversion
    if os.path.exists(binfile):
        os.unlink(binfile)
        log.log('Removed ' + binfile)
    installpath = php_build_path(subversion)
    if os.path.exists(installpath):
        shutil.rmtree(installpath)
        log.log('Deleted ' + installpath)
    servicefile = builder.get_systemd_config_path() + 'php-' + subversion + '-fpm.service'
    if os.path.exists(servicefile):
        os.remove(servicefile)
        log.log('Deleted ' + servicefile)
        service.reload_init()
        log.run(['systemctl','reset-failed','php-' + subversion + '-fpm'])
    sourcepath = build_path + 'src/php-' + fullversion + '/'
    if os.path.exists(sourcepath):
        shutil.rmtree(sourcepath)
        log.log('Deleted ' + sourcepath)

def detect_distro_code():
    """
    Attempt to determin the code that corresponds to the system's operating
    system to be used in building uw-imap.
    """
    distro_name = system.get_distro()
    if ( distro_name == 'debian' or
            distro_name == 'ubuntu' ):
        return 'ldb'
    elif ( distro_name == 'centos' or
            distro_name == 'rhel' or
            distro_name == 'rocky' or
            distro_name[:9] == 'opensuse-'):
        # version = int(system.get_distro_version())
        # if version >= 7:
        #     return 'lrh'
        # elif version >= 5:
        #     return 'lr5'
        return 'lr5'
    elif distro_name == 'macos':
        return 'oxp' # MacOS with PAM
    elif distro_name == 'cygwin':
        return 'cyg'
    elif distro_name == 'freebsd':
        return 'bsf'

def logrotate_file(username):
    """
    Get the logrotate configuration filename associated with a system user.

    Args:
        username - The system user
    """
    return settings.get('install_path') + 'etc/logrotate.d/php-sites/' + username

def add_logrotate_file(username):
    """
    Write out a configuration file for logrotated to rotate a website's php log
    files.

    Args:
        username - The system user
    """
    if not os.path.exists(primary_logrotate_file()):
        write_primary_logrotate()
    filename = logrotate_file(username)
    dirpath = os.path.dirname(filename)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    with open(filename, 'w+') as output:
        output.write('/home/' + username + '/logs/php.*.log {\n\
  weekly\n\
  rotate 52\n\
  dateext\n\
  compress\n\
  copytruncate\n\
  missingok\n\
}')

def remove_logrotate_file(username):
    """
    Remove the configuration file for logrotated to a given system user.

    Args:
        username - The system user
    """
    filename = logrotate_file(username)
    if os.path.exists(filename):
        os.remove(filename)
        return True
    return False

def primary_logrotate_file():
    return settings.get('install_path') + 'etc/logrotate.d/php.conf'

def write_primary_logrotate():
    """
    Write out a configuration file for logrotated to rotate the global php log
    files. Also add an include directive that will include all website
    logrotated files.
    """
    install_path = settings.get('install_path')
    filename = primary_logrotate_file()
    version_list = get_versions()
    if len(version_list) == 0:
        if os.path.exists(filename):
            os.remove(filename)
    else:
        with open(filename, 'w+') as output:
            output.write('include ' + install_path + 'etc/logrotate.d/php-sites\n\n')
            for version in version_list:
                output.write(php_build_path(version) + 'var/log/*.log {\n\
  weekly\n\
  rotate 52\n\
  dateext\n\
  compress\n\
  copytruncate\n\
  missingok\n\
  postrotate\n\
    /bin/kill -USR1 `cat ' + php_build_path(version) + 'var/run/php-fpm.pid 2>/dev/null` 2>/dev/null || true\n\
  endscript\n\
}\n\n')

def get_status_array():
    """
    Get the status output for each enabled version of PHP.

    Return:
        A two-dimensional array where each child element contains the following:
            A php version number
            The status output for the assicated PHP version
    """
    statuses = []
    for ver in get_versions():
        subversion = version.get_tree(ver)['sub']
        #status = subprocess.getoutput("service php-" + subversion + "-fpm status | grep '\s*[Aa]ctive:\s' | sed -E 's/\s*[Aa]ctive:\s//'")
        status = service.status("php-" + subversion + "-fpm")
        statuses.append([subversion, status])
    return statuses

class ImapBuilder(builder.AbstractGitBuilder):
    """A class to build UW IMAP from source."""
    def __init__(self):
        self.distros = False
        super().__init__('uw-imap')

    def check_build(self):
        return os.path.exists(self.source_dir() + 'tmail/tmail.o')

    def get_source_url(self):
        return 'https://github.com/uw-imap/imap.git'

    def make(self, log):
        with open(build_path + 'src/imap/ip6', 'w'):
            pass
        return log.run(['make', '-l', settings.get('max_build_load'), self.get_distro(), 'IP=6'], env=builder.build_env)

    def get_distro(self):
        distro = settings.get('imap_distro')
        if distro == 'unset':
            detected_distro = detect_distro_code()
            if detected_distro:
                distro = detected_distro
                settings.set('imap_distro', distro)
        if distro == 'unset':
            distro = self.select_distro('Select your current operating system')
            settings.set('imap_distro', distro)
        return distro

    def get_distro_list(self):
        if self.distros != False:
            return self.distros
        self.distros = []
        with open(build_path + 'src/imap/Makefile') as makefile:
            specials = False
            for line in makefile:
                if specials and len(line.strip()) == 0:
                    break
                if '# The following ports are bundled:' in line:
                    specials = True
                    continue
                if specials:
                    line = line.strip()[2:]
                    distro_code = line[:3]
                    distro_name = line[4:]
                    if ' ' in distro_code:
                        continue
                    self.distros.append( ( distro_code, distro_name ) )
        return self.distros

    def select_distro(self, query_message):
        distro_list = []
        code_list = []
        for code, name in self.get_distro_list():
            code_list.append(code)
            distro_list.append('(' + code + ')  ' + name)
        questions = [
            inquirer.List('d',
                        message=query_message,
                        choices=distro_list
                    )
        ]
        distro_list_text = inquirer.prompt(questions)['d']
        return code_list[distro_list.index(distro_list_text)]

    def install(self, log):
        pass

    def populate_config_args(self, log): # hack: using config methods to call sed in makefile
        return ['sed', '-i', r's/^\(EXTRAAUTHENTICATORS=\).*$/\1gss/', build_path + 'src/imap/Makefile']

    def source_dir(self):
        return self.build_dir + 'imap/'

    def fetch_source(self, source, log):
        super().fetch_source(source, log)
        target_dir = self.source_dir()
        log.run(['sed', '-i', r's~SSLLIB=/[^ ]* ~SSLLIB=' + build_path + r'lib ~', target_dir + 'Makefile'])
        log.run(['sed', '-i', r's~SSLINCLUDE=/[^ ]* ~SSLINCLUDE=' + build_path + r'include ~', target_dir + 'Makefile'])

    def dependencies(self):
        return ['openssl']

def get_registered_pecl_builders():
    """Get an array of all PECL builders enabled by the user."""
    pecl_builders = []
    from libsw import build_index
    builder_list = build_index.enabled_slugs()
    for possible_pecl in builder_list:
        if possible_pecl[:5] == 'pecl-':
            p_builder = build_index.get_builder(possible_pecl)
            pecl_builders.append(p_builder)
    return pecl_builders

class PhpBuilder(builder.AbstractArchiveBuilder):
    """A class to build PHP from source."""
    def __init__(self, version_str):
        self.versions = version.get_tree(version_str)
        if self.versions['sub'] == self.versions['full']:
            self.versions = version.get_tree(self.get_updated_version())
        super().__init__('php-' + self.versions['sub'])

    def get_installed_version(self):
        return get_installed_version(self.versions['sub'])

    def get_updated_version_list(self):
        return get_updated_versions()

    def get_updated_version(self):
        update_versions = self.get_updated_version_list()
        regex = re.compile(self.versions['sub'].replace('.', r'\.'))
        new_ver = False
        for v in update_versions:
            if regex.match(v):
                new_ver = v
        return new_ver

    def get_source_url(self):
        full_version = self.versions['full']
        source = 'https://www.php.net/distributions/php-' + full_version + '.tar.bz2'
        if settings.get_bool('enable_php_prerelease_version'):
            prerelease_username = get_prerelease_user()
            if '.a.' in full_version:
                source = 'https://downloads.php.net/~' + prerelease_username + '/php-' + full_version.replace('.a.', 'alpha') + '.tar.bz2'
            if '.b.' in full_version:
                source = 'https://downloads.php.net/~' + prerelease_username + '/php-' + full_version.replace('.b.', 'beta') + '.tar.bz2'
            if '.r.' in full_version:
                source = 'https://downloads.php.net/~' + prerelease_username + '/php-' + full_version.replace('.r.', 'rc') + '.tar.bz2'
            if '.R.' in full_version:
                source = 'https://downloads.php.net/~' + prerelease_username + '/php-' + full_version.replace('.R.', 'RC') + '.tar.bz2'
        return source

    def dependencies(self):
        from libsw import build_index
        deps = ['openssl', 'uw-imap', 'curl']
        for pecl_builder in get_registered_pecl_builders():
            deps.append(pecl_builder.slug)
        if 'postgresql' in build_index.enabled_slugs():
            deps.append('postgresql')
        return deps

    # def get_config_arg_file(self):
    #     config_folder = settings.get('install_path') + 'etc/build-config/'
    #     return [
    #         config_folder + self.slug,
    #         config_folder + self.slug + '-' + self.versions['major'],
    #         config_folder + self.slug + '-' + self.versions['sub'],
    #     ]

    def get_config_arg_file(self):
        config_folder = settings.get('install_path') + 'etc/build-config/'
        return self.get_folder_config_args(config_folder)

    def get_user_config_arg_file(self):
        config_folder = settings.get('install_path') + 'etc/build-config/user/'
        return self.get_folder_config_args(config_folder)

    def get_folder_config_args(self, config_folder):
        elements = []
        no_version_file = config_folder + 'php'
        if os.path.exists(no_version_file):
            elements.append(no_version_file)
        search = no_version_file + '-*'
        print('looking for config files: ' + search)
        install_segments = self.versions['full'].split('.')
        for entry in glob.glob(search):
            version_name = entry[len(no_version_file)+1:]
            if version.is_search_in_version(version_name ,self.versions):
                elements.append(entry)
        return elements

    def install(self, log):
        super().install(log)
        deploy_environment(self.versions, log)

    def uninstall(self, log):
        log.log('Uninstalling ' + self.slug)
        remove_environment(self.versions['sub'], log)
        log.log(self.slug + ' uninstalled')

    def uninstall_warnings(self):
        vhost_directory = vhost_path(self.versions['sub'])
        file_list = glob.glob(vhost_directory + '*.conf')
        file_list.extend(glob.glob(vhost_directory + '*.conf.disabled'))
        if len(file_list) > 0:
            warning = 'There are still enabled/disabled sites for ' + self.slug + ':\n'
            for file in file_list:
                warning += file + '\n'
            return warning
        else:
            return False

    def build(self):
        if not os.path.exists(self.build_dir + 'imap/c-client/imap4r1.o'):
            ImapBuilder().build()
        self.source_version = self.versions['full']
        return super().build()

    def deploy(self, remote_address, log):
        self.source_version = self.versions['full']
        return super().deploy(remote_address, log)


    def populate_config_args(self, log, command=False):
        from libsw import build_index
        if command == False:
            command = ['./configure'];
        command.append('--prefix=' + php_build_path(self.versions['sub']))
        command.append('--with-mysql-sock=' + settings.get('mysql_socket'))
        for pecl_builder in get_registered_pecl_builders():
            command.append(pecl_builder.get_php_build_arg())
        if 'postgresql' in build_index.enabled_slugs():
            command.append('--with-pgsql=' + build_path + 'pgsql/')
            command.append('--with-pdo-pgsql=' + build_path + 'pgsql/')
        return super().populate_config_args(log, command)

    def source_dir(self):
        full_version = self.source_version
        if settings.get_bool('enable_php_prerelease_version'):
            if '.a.' in full_version:
                full_version = full_version.replace('.a.', 'alpha')
            if '.b.' in full_version:
                full_version = full_version.replace('.b.', 'beta')
            if '.r.' in full_version:
                full_version = full_version.replace('.r.', 'rc')
            if '.R.' in full_version:
                full_version = full_version.replace('.R.', 'RC')
        return self.build_dir + 'php-' + full_version + '/'

    def log_name(self):
        version = self.source_version
        if version == False:
            version = self.versions['full']
        return settings.get('install_path') + 'var/log/build/php-' + version + '.log'

    def update_if_needed(self):
        old = self.get_installed_version()
        new = self.get_updated_version()
        if version.first_is_higher(new, old):
            self.versions = version.get_tree(new)
            return self.build()
        return False, False

    def cleanup_old_versions(self, log):
        found = False
        found_version = False
        for logname in builder.find_old_build_elements(settings.get('install_path') + 'var/log/build/php-' + self.versions['sub'] + '.', '.log'):
            os.remove(logname)
            log.log("Removed old log file " + logname)
        for folder in builder.find_old_build_elements(build_path + 'src/php-' + self.versions['sub'] + '.', '/'):
            shutil.rmtree(folder)
            log.log("Removed old source directory " + folder)

    def run_pre_config(self, log):
        rebuild_config = False
        ext_dir = self.source_dir() + 'ext/'
        for pecl_builder in get_registered_pecl_builders():
            pecl_dir = pecl_builder.source_dir()
            target_dir = ext_dir + pecl_builder.get_pecl_slug() + '/'
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.copytree(pecl_dir, target_dir)
            rebuild_config = True
        if rebuild_config:
            log.log('Rebuilding PHP configure file to include PECL libraries')
            os.remove(self.source_dir() + 'configure')
            log.run([self.source_dir() + 'buildconf', '--force'], env=builder.build_env)
        if version.first_is_higher('8.0.9999', self.versions['full']):
            remove_ssl2(log, self.source_dir() + 'ext/openssl/openssl.c')

def is_same_subversion(versions, version_string):
    """Determine if two versions have the same first two numbers."""
    ver2 = version.get_tree(version_string)
    return versions['sub'] == ver2['sub']

class OpenSSL3Complier(file_filter.FileFilter):
    def __init__(self, file, log):
        self.log = log
        super().__init__(file)

    def filter_stream(self, in_stream, out_stream):
        updated = False
        for line in in_stream:
            if 'RSA_SSLV23_PADDING' in line:
                out_stream.write('#ifdef RSA_SSLV23_PADDING\n')
                out_stream.write(line)
                out_stream.write('#endif\n')
                updated = True
                self.log.log('Forced compatibility with OpenSSL 3')
            else:
                out_stream.write(line)
        return updated


def remove_ssl2(log, source_file):
    OpenSSL3Complier(source_file, log).run()
