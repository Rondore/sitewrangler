#!/usr/bin/env python3

import os
import re
import inquirer
import glob
import subprocess
import requests
import tarfile
from libsw import logger, builder, openssl, settings, service, user, input_util, file_filter

modsec_exception_dir = settings.get('install_path') + 'etc/modsec/sites/'
nginx_dir = settings.get('build_path') + 'nginx/'
vhost_dir = nginx_dir + 'conf/vhosts/'
binary_file =  nginx_dir + 'sbin/nginx'

def reload():
    """
    Have nginx reload it's configuration from disk.
    """
    service.reload('nginx')
    #os.system(binary_file + ' -s reload')

def get_modsec_path(domain):
    """
    Get the full path of the ModSecurity rule exception file for a given domain.

    Args:
        domain - The domain associated with the ModSecurity file
    """
    return modsec_exception_dir + domain

def get_vhost_path(domain):
    """
    Get the full path of the vhost configuration file for a given domain.

    Args:
        domain - The domain associated with the vhost file
    """
    path = vhost_dir + domain + '.conf'
    disabled_path = vhost_dir + domain + '.conf.disabled'
    if os.path.exists(disabled_path) and not os.path.exists(path):
        return disabled_path
    return path

def choose_template(query_message, hide_ssl=False):
    """
    Prompt the user to select a vhost template file.

    Args:
        query_message - The message to display to the user in the prompt
        hide_ssl - Only show non-SSL templates
    """
    templates = template_list()
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=templates
                )
    ]
    conf_file = inquirer.prompt(questions)['f']
    return conf_file

def template_list(hide_ssl=False):
    """
    Get an array containing all of the nginx vhost template file names exluding
    path.

    Args:
        hide_ssl - Only show non-SSL templates
    """
    templates = []
    folder_name = settings.get('install_path') + 'etc/nginx-templates/'
    for temp in glob.glob(folder_name + '*'):
        is_ssl = temp.endswith('-ssl') or temp.endswith('-hsts')
        if not hide_ssl or not is_ssl:
            templates.append(temp[len(folder_name):])
    custom_folder_name = folder_name + 'custom/'
    for temp in glob.glob(custom_folder_name + '*'):
        is_ssl = temp.endswith('-ssl') or temp.endswith('-hsts')
        if not hide_ssl or not is_ssl:
            name = temp[len(folder_name):]
            if name not in templates:
                templates.append(name)
    return sorted(templates)

def is_template(name):
    """
    Check if a given string matches the filename of a vhost template file.

    Args:
        name - The template filename to test
    """
    return os.path.exists(get_template_path(name))

def get_template_path(name):
    """
    Get the full path for a given nginx vhost template name.

    Args:
        name - The name (slug) of the template
    """
    folder_name = settings.get('install_path') + 'etc/nginx-templates/'
    custom_folder_name = folder_name + 'custom/'
    if os.path.exists(custom_folder_name + name):
        return custom_folder_name + name
    return settings.get('install_path') + 'etc/nginx-templates/' + name

def replace_template_line(line, needle, replacement, is_header=False):
    """
    Filter a line read from a template file replacing any instances of a variable name
    with its value. While filtering a header line. Field names are only replaced after
    the second colin to avoid replacing the first use of the name. This is to ensure
    that both the name and values of these extra values can still be interpreted by code.

    Args:
        line - The line of text that needs to be filtered 
        needle - The variable name that needs to be replaced
        replacement - The value of the varable used to replace the name
        is_header - True only if the line is part of the template header
    """
    custom_field = False
    if is_header:
        if re.search('^# Field', line):
            first_colin = line.find(":")
            if first_colin != -1:
                second_colin = line.find(":", first_colin + 1)
                if second_colin != -1:
                    key = line[first_colin+1:second_colin].strip()
                    if key == needle:
                        line = line[0:second_colin] + ': ' + replacement + '\n'
                    custom_field = True
    if not custom_field:
        line = line.replace(needle, replacement)
    return line

def write_vhost_with_variables(open_template_file, open_vhost_file, variable_array):
    """
    Write a vhost file using a template to read from and an array of values to replace.

    Args:
        open_template_file - The already open template file from which to read 
        open_vhost_file - The already open vhost file for writing
        variable_array - Template values stored as [name, value] within a parent array
    """
    header = True
    header_needle = re.compile('^#')
    for line in open_template_file:
        if header:
            if header_needle.search(line) == None:
                header = False
        for key, value in variable_array:
            line = replace_template_line(line, key, value, header)
        open_vhost_file.write(line)

def append_missing_variable(variable_array, key, value):
    """
    Add a value that is used for populating a vhost file if not already present.
    Each value is stored as [name, value] within the parent array.

    Args:
        variable_array - The parrent array into which the value is added if missing
        key - The name of the variable
        value - The value of the variable
    """
    found = False
    for ke, val in variable_array:
        if key == ke:
            found = True
            break
    if not found:
        variable_array.append([key, value])
    return variable_array

def populate_default_vhost_variables(username, domain, existing_fields=[]):
    """
    Add any missing standard values that are used for populating a vhost file.
    Each value is stored as [name, value] within the parent array.

    Args:
        username - The system user assiciated with the website
        domain - The domain name assiciated with the website without www
        existing_fields - The parrent array into which any missing values are added
    """
    modsec = get_modsec_path(domain)
    home = user.home_dir(username)
    dash_domain = domain.replace('.', '-', 100)
    under_domain = domain.replace('.', '_', 100)
    local_ip = settings.get('local_ip')
    public_ip = settings.get('public_ip')
    ip6 = settings.get('ip6')
    build_path = settings.get('build_path')
    install_path = settings.get('install_path')
    if not ip6 or ip6 == 'False':
        ip6 = '::'
    if not local_ip or local_ip == 'False':
        local_ip = '0.0.0.0'
    if not os.path.exists(modsec_exception_dir):
        os.makedirs(modsec_exception_dir)
    if not os.path.exists(vhost_dir):
        os.makedirs(vhost_dir)
    with open(modsec, 'a+'):
        pass
    existing_fields = append_missing_variable(existing_fields, 'DOMAINNAMEE', domain)
    existing_fields = append_missing_variable(existing_fields, 'USERNAMEE', username)
    existing_fields = append_missing_variable(existing_fields, 'DASHDOMAINN', dash_domain)
    existing_fields = append_missing_variable(existing_fields, 'UNDERDOMAINN', under_domain)
    existing_fields = append_missing_variable(existing_fields, 'HOMEDIRR', home)
    existing_fields = append_missing_variable(existing_fields, 'LOCALIPP', local_ip)
    existing_fields = append_missing_variable(existing_fields, 'PUBLICIPP', public_ip)
    existing_fields = append_missing_variable(existing_fields, 'IPV66', ip6)
    existing_fields = append_missing_variable(existing_fields, 'MODSECC', modsec)
    existing_fields = append_missing_variable(existing_fields, 'BUILDPATHH', build_path)
    existing_fields = append_missing_variable(existing_fields, 'INSTALLPATHH', install_path)
    return existing_fields

def make_vhost(username, domain, template_name='php', template_fields=False):
    """
    Create a new vhost file for a given domain.

    Args:
        username - The system username that stores the sitesfiles
        domain - The domain associated with the new vhost file
        template_name - The name of the nginx vhost template to use
    """
    read_path = get_template_path(template_name)
    vhost_path = get_vhost_path(domain)
    
    if not template_fields:
        fields = get_vhost_headers(read_path)[0]
        template_fields = []
        for key, value in fields:
            value = input_util.prompt_value(key, value)
            template_fields.append([key, value])
        template_fields = populate_default_vhost_variables(username, domain, template_fields)
    with open(read_path) as template:
        with open(vhost_path, 'w') as host:
            write_vhost_with_variables(template, host, template_fields)
    print('Created ' + vhost_path)
    reload()

def edit_vhost(domain):
    """
    Allow the user to edit a vhost file with the system text edior, reloading
    the nginx configuration if modified.

    Args:
        domain - The domain associated with the nginx vhost file
    """
    path = get_vhost_path(domain)
    if input_util.edit_file(path):
        print('Reloading nginx configuration to apply changes.')
        reload()

def get_vhost_headers(file_path):
    """
    Get an array of values stored in a vhost header. Each value is stored as
    [name, value] within the parent array.

    Args:
        file_path - An array of header values
    """
    username = ''
    domain = ''
    template = ''
    fields = []
    field_needle = re.compile('^# Field')
    field_header_extract = re.compile('(.*:\s*)(\S+)(\s*:\s*)(.*)')

    user_needle = re.compile('^# User')
    domain_needle = re.compile('^# Domain')
    template_needle = re.compile('^# Template')
    header_extract = re.compile('(.*:\s*)(.*)')

    with open(file_path) as read:
        for line in read:
            if len(line) == 0:
                break
            if user_needle.search(line) != None:
                username = header_extract.search(line).group(2)
            if domain_needle.search(line) != None:
                domain = header_extract.search(line).group(2)
            if template_needle.search(line) != None:
                template = header_extract.search(line).group(2)
            if field_needle.search(line) != None:
                field_fieldes = field_header_extract.search(line)
                key = field_fieldes.group(2)
                value = field_fieldes.group(4)
                fields.append([key, value])
    return fields, username, domain, template


def add_ssl_to_site_hosts(domain):
    """
    Replace a non-SSL nginx vhost configuration file with it's corresponding
    SSL-enabled version. If there are already SSL configuration lines detected
    in the file, it will not be modified.

    Args:
        domain - The domain associated with the nginx vhost file
    """
    full_file = get_vhost_path(domain)
    fields, username, domain, template = get_vhost_headers(full_file)
    fields = populate_default_vhost_variables(username, domain, fields)

    if not (template.endswith('-ssl') or template.endswith('-hsts')):
        template += '-ssl'
    template_path = get_template_path(template)

    if not os.path.exists(template_path):
        print('Unable to find template: ' + template)
        return False

    with open(template_path) as template_file:
        with open(full_file, 'w') as vhost:
            write_vhost_with_variables(template_file, vhost, fields)
    reload()
    print('Updated ' + full_file)
    return True


def retemplate_vhost(domain):
    """
    Reapply an nginx vhost template to a website's vhost file. This is most useful
    when a template has been updated and that update needs to be applied to the
    given website.

    Args:
        domain - The domain associated with the nginx vhost file
    """
    full_file = get_vhost_path(domain)
    fields, username, domain, template = get_vhost_headers(full_file)
    fields = populate_default_vhost_variables(username, domain, fields)
    template_path = get_template_path(template)

    if not os.path.exists(template_path):
        print('Unable to find template: ' + template)
        return False

    with open(template_path) as template_file:
        with open(full_file, 'w') as vhost:
            write_vhost_with_variables(template_file, vhost, fields)
    reload()
    print('Updated ' + full_file)
    return True

def enabled_sites():
    """
    Get an array of all domains with enabled vhost files.
    """
    domains = []
    for file in glob.glob(vhost_dir + '*.conf'):
        domains.append(file[len(vhost_dir):-5])
    return sorted(domains)

def select_conf(query_message):
    """
    Have the user select from a list of all domains with enabled vhost files.

    Args:
        query_message - The message to display to the user in the prompt
    """
    files = enabled_sites()
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=files
                )
    ]
    conf_file = inquirer.prompt(questions)['f']
    return conf_file

def disabled_sites():
    """
    Get an array of all domains with disabled vhost files.
    """
    domains = []
    for file in glob.glob(vhost_dir + '*.conf.disabled'):
        domains.append(file[len(vhost_dir):-14])
    return sorted(domains)

def select_disabled_conf(query_message):
    """
    Have the user select from a list of all domains with disabled vhost files.

    Args:
        query_message - The message to display to the user in the prompt
    """
    files = disabled_sites()
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=files
                )
    ]
    conf_file = inquirer.prompt(questions)['f']
    return conf_file

def enable_vhost(domain):
    """
    Remove the suffix ".disabled" from a vhost file and reload nginx, thereby
    enabling the site/file.

    Args:
        domain - The domain to enable
    """
    source = vhost_dir + domain + '.conf.disabled'
    target = vhost_dir + domain + '.conf'
    if os.path.exists(source):
        os.rename(source, target)
        reload()
        return True
    else:
        return False

def disable_vhost(domain):
    """
    Append the suffix ".disabled" to a vhost file and reload nginx, thereby
    disabling the site/file.

    Args:
        domain - The domain to disable
    """
    source = vhost_dir + domain + '.conf'
    target = vhost_dir + domain + '.conf.disabled'
    if os.path.exists(source):
        os.rename(source, target)
        reload()
        return True
    else:
        return False

def remove_vhost(domain):
    """
    Delete the nginx vhost file associated with a domain and then reload nginx.

    Args:
        domain - Delete the file associated with this domain
    """
    modsec = get_modsec_path(domain)
    enabled_path = vhost_dir + domain + '.conf'
    disabled_path = vhost_dir + domain + '.conf.disabled'
    removed = False
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
        removed = True
    if os.path.exists(disabled_path):
        os.remove(disabled_path)
        removed = True
    if os.path.exists(modsec):
        os.remove(modsec)
    if removed:
        reload()
    return removed

def get_user_domains(username):
    """
    Get domain names associated with a system user.

    Args:
        username - The system user
    """
    enabled_domains = []
    for domain in enabled_sites():
        if username == user_from_domain(domain, only='enabled'):
            enabled_domains.append(domain)
    disabled_domains = []
    for domain in disabled_sites():
        if username == user_from_domain(domain, only='disabled'):
            disabled_domains.append(domain)
    return [enabled_domains, disabled_domains]

def user_from_domain(domain, only=False):
    """
    Get the system user associated with a domain based on the contents of the
    domain's nginx vhost file.

    Args:
        domain - The domain used in finding the system user
        only - Limit returned values to sites that are enabled or disabled. Values must be False, 'enabled' or 'disabled'
    """
    vhost = get_vhost_path(domain)
    if only == 'enabled' and vhost[-9:] == '.disabled':
        return False
    if only == 'disabled' and vhost[-9:] != '.disabled':
        return False
    header_match = re.compile('^#')
    line_match = re.compile('^#\s*User\s*:')
    if os.path.exists(vhost):
        with open(vhost) as v:
            for line in v:
                if header_match.match(line) == None:
                    break
                match = line_match.match(line)
                if match != None:
                    return line.split(':')[1].strip()
    return False

def docroot_from_domain(domain):
    """
    Get path of the document root directory associated with a domain based on
    the contents of the domain's nginx vhost file.

    Args:
        domain - The domain used in finding the document root
    """
    vhost = get_vhost_path(domain)
    line_match = re.compile('^[ \s]*root')
    line_extract = re.compile('.*root[ \s]*([^;]*)[ \s]*;.*')
    if os.path.exists(vhost):
        with open(vhost) as v:
            for line in v:
                match = line_match.match(line)
                if match != None:
                    extract = line_extract.sub(r'\1', line)
                    if len(extract) > 0:
                        path = extract.strip()
                        if not path.endswith('/'):
                            path += '/'
                        return path
    return False

def deploy_environment(log, first_install):
    """
    Install an nginx systemd init file if needed, then start nginx.

    Args:
        log - An open log to write to
        first_install - A boolean value indicating if this is the first time this function has been run
    """
    systemd_file = builder.get_systemd_config_path() + 'nginx.service'
    install_path = settings.get('install_path');

    if first_install:
        #TODO add these lines to /opt/sitewrangler/usr/local/nginx/conf/nginx.conf with a FileFilter
        with open(nginx_dir + 'conf/nginx.conf', 'w+') as out:
            out.write('''
user  daemon daemon;
worker_processes  auto;

error_log  "logs/error.log";

pid        "logs/nginx.pid";

events {
    use                 epoll;
    worker_connections  1024;
    multi_accept        on;
}


http {
    include       mime.types;
    default_type  application/octet-stream;
    server_names_hash_bucket_size 128;

    client_body_temp_path  "client_body_temp" 1 2;
    proxy_temp_path "proxy_temp" 1 2;
    fastcgi_temp_path "fastcgi_temp" 1 2;
    scgi_temp_path "scgi_temp" 1 2;
    uwsgi_temp_path "uwsgi_temp" 1 2;

    access_log  "logs/access.log";

    modsecurity on;''' + 
'    modsecurity_rules_file "' + install_path + 'etc/modsec/rules.conf";' +
'''
    sendfile        on;

    gzip on;
    gzip_http_version 1.1;
    gzip_comp_level 2;
    gzip_proxied any;
    gzip_vary on;
    gzip_types text/plain
               text/xml
               text/css
               text/javascript
               application/json
               application/javascript
               application/x-javascript
               application/ecmascript
               application/xml
               application/rss+xml
               application/atom+xml
               application/rdf+xml
               application/xml+rss
               application/xhtml+xml
               application/x-font-ttf
               application/x-font-opentype
               application/vnd.ms-fontobject
               image/svg+xml
               image/x-icon
               application/atom_xml;

    gzip_buffers 16 8k;

    add_header X-Frame-Options SAMEORIGIN;

    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_buffer_size 8k;
    ssl_ciphers 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256';
    ssl_ecdh_curve secp384r1;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;

    keepalive_timeout 5m;

    include blocklist.conf;

    server {
        return 404;
    }

    ##
    # Virtual Host Configs
    ##
    include vhosts/*.conf;
}
''')
        new = "    modsecurity on;\n" + \
            "    modsecurity_rules_file " + settings.get('install_path') + "etc/modsec/rules.conf;\n"
    blockfile = nginx_dir + 'conf/blocklist.conf'
    if not os.path.isfile(blockfile):
        with open(blockfile, 'a+'):
            pass

    if os.path.isfile(systemd_file):
        service.restart('nginx', log)
    else:
        with open(systemd_file, 'w+') as unit_file:
            unit_file.write('[Unit]\n')
            unit_file.write('Description=The Nginx Webserver and Proxy\n')
            unit_file.write('Wants=network-online.target\n')
            unit_file.write('After=network-online.target\n')
            unit_file.write('\n')
            unit_file.write('[Service]\n')
            unit_file.write('Type=forking\n')
            unit_file.write('PIDFile=' + nginx_dir + 'logs/nginx.pid\n')
            unit_file.write('ExecStartPre=' + binary_file + ' -t\n')
            unit_file.write('ExecStart=' + binary_file + '\n')
            unit_file.write('ExecReload=' + binary_file + ' -s reload\n')
            unit_file.write('ExecStop=' + binary_file + ' -s stop\n')
            unit_file.write('PrivateTmp=true\n')
            unit_file.write('Restart=always\n')
            unit_file.write('RestartSec=3\n')
            unit_file.write('Environment="LD_LIBRARY_PATH=' + builder.ld_path + '"\n')
            unit_file.write('\n')
            unit_file.write('[Install]\n')
            unit_file.write('WantedBy=multi-user.target\n')

        service.reload_init(log)
        service.enable('nginx', log)
        service.start('nginx', log)

    if not os.path.isfile(logrotate_file()):
        write_logrotate()


def check_dhparams():
    """
    Create dhparam if it does not already exist on the system.
    """
    filename = '/etc/ssl/certs/dhparam.pem'
    build_path = settings.get('build_path');
    if not os.path.exists(filename):
        subprocess.run([build_path + 'bin/openssl', 'dhparam', '-dsaparam', '-out', filename, '4096'], env=builder.build_env)

def get_rule_bypass_line(rule_id):
    """
    Get the coniguration line to use to bypass a ModSecurity rule.

    Args:
        rule_id - The numerical id of the ModSecurity rule
    """
    return "SecRuleRemoveById " + rule_id

def bypass_modsec_rule(domain, rule_id):
    """
    Disable a ModSecurity rule for a domain.

    Args:
        domain - The domain to disabled the rule for
        rule_id - The numerical id of the ModSecurity rule to disable
    """
    filename = get_modsec_path(domain)
    rule = get_rule_bypass_line(rule_id)
    file_filter.AppendUnique(filename, rule).run()
    reload()

def unbypass_modsec_rule(domain, rule_id):
    """
    Un-Disable a ModSecurity rule for a domain.

    Args:
        domain - The domain to un-disable the rule for
        rule_id - The numerical id of the ModSecurity rule to disable
    """
    filename = get_modsec_path(domain)
    rule = get_rule_bypass_line(rule_id)
    file_filter.RemoveExact(filename, rule).run()
    reload()

def get_bypassed_modsec_rules(domain):
    """
    Get a list of all rules that have been disabled for a domain.

    Args:
        domain - The domain to check
    """
    filename = get_modsec_path(domain)
    rules = []
    if os.path.exists(filename):
        with open(filename) as rule_file:
            for line in rule_file:
                if line.startswith('SecRuleRemoveById '):
                    rule_id = line[18:].strip()
                    rules.append(rule_id)
    return rules

def logrotate_file():
    return settings.get('install_path') + 'etc/logrotate.d/nginx.conf'

def write_logrotate():
    """
    Write out a configuration file for logrotated to rotate the global php log
    files. Also add an include directive that will include all website
    logrotated files.
    """
    install_path = settings.get('install_path')
    filename = logrotate_file()
    with open(filename, 'w+') as output:
        output.write(nginx_dir + 'logs/*.log {\n\
    weekly\n\
    rotate 52\n\
    dateext\n\
    compress\n\
    copytruncate\n\
    missingok\n\
    postrotate\n\
	/bin/kill -USR1 `cat ' + nginx_dir + 'logs/nginx.pid 2>/dev/null` 2>/dev/null || true\n\
    endscript\n\
}\n\n')

class NginxBuilder(builder.AbstractArchiveBuilder):
    """
    A class to build nginx from source.
    """
    def __init__(self):
        super().__init__('nginx')

    def get_installed_version(self):
        about_text = subprocess.getoutput(builder.set_sh_ld + binary_file + ' -v')
        match = re.match(r'nginx version: nginx/([0-9\.]*)', about_text)
        if match == None:
            return '0'
        version = match.group(1)
        return version

    def get_updated_version(self):
        request = requests.get('https://nginx.org/en/download.html')
        split1 = re.compile(r'.*Stable(.*)')
        split2 = re.compile(r'(<a [^>]*>)')
        regex = re.compile(r'/download/nginx')
        clean = re.compile(r'.*href="/download/nginx\-([0-9\.]*)\.tar\.gz".*')

        for line in request.text.splitlines():
            line = split1.sub(r'\1', line)
            line = split2.sub('\\1\n', line)
            for sub_line in line.splitlines():
                match = regex.search(sub_line)
                if match == None:
                  continue
                return clean.sub(r'\1', sub_line)
        return False

    def populate_config_args(self, log, command=['./configure']):
        build_path = settings.get('build_path');
        ssl_ver = openssl.OpensslBuilder().get_installed_version()
        command.append('--with-openssl=' + build_path + 'src/openssl-' + ssl_ver)
        return super().populate_config_args(log, command)

    def get_source_url(self):
        return 'https://nginx.org/download/nginx-' + self.source_version + '.tar.gz'

    def dependencies(self):
        return ['openssl', 'modsec-nginx', 'cache-nginx']

    def get_build_env(self):
        mod_lib = builder.get_pkg_config_var('modsecurity','libdir')
        nginx_env = dict(super().get_build_env())
        nginx_env['MODSECURITY_LIB'] = mod_lib
        nginx_env['MODSECURITY_INC'] = builder.build_path + 'include/'
        return nginx_env

    def install(self, log):
        first_install = False
        if not os.path.exists(nginx_dir + 'conf/nginx.conf'):
            first_install = True
        check_dhparams()
        super().install(log)
        if not os.path.exists(nginx_dir + 'cache/'):
            os.makedirs(nginx_dir + 'cache/')
        deploy_environment(log, first_install)

class AbstractNginxModuleBuilder(builder.AbstractGitBuilder):
    """A class to build the ModSecurity module for nginx from source."""

    def install(self, log):
        pass

    def make(self, log):
        return 0

    def populate_config_args(self, log):
        return []

    def clean(self, log):
        pass

class ModSecurityNginxBuilder(AbstractNginxModuleBuilder):
    """A class to fetch the source code for the ModSecurity module for nginx."""
    def __init__(self):
        super().__init__('modsec-nginx')

    def check_build(self):
        return True # os.path.exists(self.source_dir() + 'tools/rules-check/modsec_rules_check-rules-check.o')

    def get_source_url(self):
        return 'https://github.com/SpiderLabs/ModSecurity-nginx.git'

    def dependencies(self):
        return ['modsec']

    def source_dir(self):
        return self.build_dir + 'ModSecurity-nginx/'

class NginxCacheBuilder(AbstractNginxModuleBuilder):
    """A class to fetch the cache module for nginx."""
    def __init__(self):
        super().__init__('cache-nginx')

    def check_build(self):
        return True # os.path.exists(self.source_dir() + 'tools/rules-check/modsec_rules_check-rules-check.o')

    def get_source_url(self):
        return 'https://github.com/FRiCKLE/ngx_cache_purge'

    def dependencies(self):
        return []

    def source_dir(self):
        return self.build_dir + 'ngx_cache_purge/'
