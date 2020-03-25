#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw deploy update [force]  # Install locally built packages on all production servers that do not use the same package version')
    print('sw deploy checkupdate  # Check locally built packages against all production servers and list those that do not use the same package version')
    print('sw deploy (add|create) [ip_addr]  # Register an IP address as a production server (be sure to authenticate SSH keys first)')
    print('sw deploy (delete|remove) [ip_addr]  # Unregister an IP address as a production server')
    print('sw deploy list  # List all servers set for remote package deployment')
    # print("sw deploy run [example]  # Install one locally built (and it's dependencies) package on all production servers that do not use the same package version")
index = command_index.CategoryIndex('deploy', _help)

def _update(force):
    if force:
        force = force.lower()
        if force != 'force':
            force = False
    from libsw import deploy
    deploy.deploy(force)
index.register_command('update', _update)
index.register_command('upgrade', _update) # for yum/dnf habits :)

def _checkupdate():
    from libsw import deploy
    deploy.check_deploy()
index.register_command('checkupdate', _checkupdate)
index.register_command('check-update', _checkupdate) # for apt habits :)

# def _run(first, more):
#     from libsw import build_queue, build_index
#     build_list = []
#     if not first:
#         build_list = build_index.select_slugs('Select software to build')
#     else:
#         build_list.append(first)
#         if more:
#             for item in more:
#                 build_list.append(item)
#     queue = build_queue.TargetedQueue(build_list)
#     build_index.Index().populate_builders(queue)
#     if queue.run() == 0:
#         print("Unable to build " + build_list[0])
# index.register_command('run', _run)

def _list():
    from libsw import deploy
    ip_list = deploy.get_registered_ips()
    for ip in ip_list:
        print(ip)
index.register_command('list', _list)

def _add(ip):
    from libsw import input_util, deploy
    if ip == False or not input_util.is_ip(ip):
        ip = input_util.input_ip()
    if deploy.register_ip(ip):
        print('Added ' + ip + ' to deployment targets')
    else:
        print('Unable to add ' + ip + ' to deployment targets. (already added?)')
index.register_command('add', _add)
index.register_command('create', _add)

def _remove(ip):
    from libsw import input_util, deploy
    if ip == False or not input_util.is_ip(ip):
        ip = input_util.input_ip()
    if deploy.unregister_ip(ip):
        print('Removed ' + ip + ' from deployment targets')
    else:
        print('Unable to remove ' + ip + ' from deployment targets. (already removed?)')
index.register_command('remove', _remove)
index.register_command('delete', _remove)