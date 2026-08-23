#!/usr/bin/env python3

import subprocess
import os

from libsw import file_filter, settings, build_queue, build_index, logger, system

def register_ip(ip):
    path = settings.get('install_path') +  'etc/remote-deploy'
    add_podman_connection(ip)
    return file_filter.AppendUnique(path, ip, True).run()

def unregister_ip(ip):
    path = settings.get('install_path') +  'etc/remote-deploy'
    return file_filter.RemoveExact(path, ip).run()

def get_registered_ips():
    path = settings.get('install_path') +  'etc/remote-deploy'
    if not os.path.exists(path):
        return []
    ip_list = []
    with open(path, 'r') as ip_file:
        for line in ip_file:
            line = line.strip()
            if len(line) > 0:
                ip_list.append(line)
    return ip_list

def init(ip):
    if ip in get_registered_ips():
        subprocess.run(['ssh', 'root@' + ip, 'cd /opt/ && ' +
                        'git clone -b "' + system.get_sw_branch() + '" https://github.com/Rondore/sitewrangler.git && ' +
                        'cd sitewrangler && ' +
                        './bin/installCore.sh'])
    else:
        return None

def deploy(force):
    log_path = settings.get('install_path') +  'var/log/remote-deploy'
    with open(log_path, 'a+') as log_file:
        log = logger.Log(log_file)
        queue = build_queue.new_queue(force)
        build_index.Index().populate_builders(queue)
        queue.run()
        if queue.failed():
            log.log('Error: Unable to deploy. Build failed.')
        else:
            for ip in get_registered_ips():
                log.log('')
                log.log('Checking deployment for ' + ip)
                queue.set_failed_file(settings.get('install_path') + 'etc/deploy-failures/' + ip)
                for builder, status in queue.queue:
                    status = get_deploy_live_status(ip, log, force, queue, builder)
                    log.log(builder.slug + ' ' + status)
                    if status == 'ready':
                        builder.deploy(ip, log)

def check_deploy():
    log = logger.Log()
    queue = build_queue.new_queue()
    build_index.Index().populate_builders(queue)
    update_list = queue.run_check()
    if len(update_list) > 0:
        log.log("Error: Software must be updated locally first.")
    else:
        for ip in get_registered_ips():
            log.log('')
            log.log('Checking deployment for ' + ip)
            queue.set_failed_file(settings.get('install_path') + 'etc/deploy-failures/' + ip)
            for builder, status in queue.queue:
                status = get_deploy_live_status(ip, log, False, queue, builder)
                log.log(builder.slug + ' ' + status)

debug = False
def get_deploy_live_status(ip, log, force, queue, builder, level=0):
    """
    Recalculate the status of a builder deployment by checking it's dependencies.

    Args:
        builder - The builder to check
        level - The recursive depth level the status check is in
    """
    status = 'missing'
    for b, s in queue.queue:
        if b is builder:
            status = s
    if status == '' or status == 'waiting':
        if status == '' and not builder.needs_deploy(ip, log, force):
            status = 'pass'
        else:
            status = 'ready'
        deps = builder.dependencies()
        if len(deps) > 0:
            for slug in deps:
                dep_builder, dep_status = queue.entry(slug)
                if dep_status == False:
                    log.log('Unable to find package "' + slug + '" needed for "' + builder.slug + '"')
                    return 'failed'
                dep_status = get_deploy_live_status(ip, log, force, queue, dep_builder, level + 1)
                if dep_status == 'failed' or dep_status == 'missing':
                    return 'failed'
                elif dep_status == 'waiting' or dep_status == 'ready':
                    status = 'waiting'
                elif dep_status == 'done':
                    if status != 'waiting':
                        status = 'ready'

    if debug:
        dmsg = 'Checking:'
        for i in range(level):
            dmsg += ' '
        dmsg += builder.slug + ' ' + status
        print(dmsg)
    return status

def get_remote_enabled_packages(ip: str) -> list[str]:
    """
    Get a list of all packages enabled on a remote ip
    """
    if ip in get_registered_ips():
        remote_command = 'cat "$(sw setting get install_path)/etc/enabled-packages" 2>/dev/null'
        process = subprocess.run(['ssh', 'root@' + ip, remote_command], capture_output=True)
        if process.returncode == 0:
            return process.stdout.decode().splitlines()
    return []

def add_podman_connection(ip: str, identity_file: str | None = None):
    if not identity_file:
        identity_file = settings.get('ssh_key')
    subprocess.run(['podman', 'system', 'connection', 'add', '--identity', identity_file, ip, 'root@' + ip])

def remove_podman_connection(ip: str):
    subprocess.run(['podman', 'system', 'connection', 'remove', ip])

def push(ip: str):
    print('Pusing to ' + ip)
    containers = get_remote_enabled_packages(ip)
    for name in containers:
        subprocess.run(['podman', 'image', 'scp', 'localhost/sitewrangler/' + name, ip + '::'])