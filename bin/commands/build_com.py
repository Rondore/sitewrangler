#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw build update [force]  # Update softare sources and build anthing that needs building')
    print('sw build checkupdate  # Check for updates to software sources and print a list of slugs that need updating')
    print('sw build list  # List all software slugs enabled on the system')
    print('sw build run [example]  # Rebuild a given (list of) software slug(s) and other software that depends on it')
    print('sw build log [example]  # Show the build log for the given software slug')
    print('sw build freeze [slug]  # Prevent a software package from updating to a newer version')
    print('sw build (unfreeze|thaw) [slug]  # Allow a software package to update to a newer version')
    print('sw build list(freeze|frozen)  # List software set to not update')
index = command_index.CategoryIndex('build', _help)

def _update(force):
    if force:
        force = force.lower()
        if force != 'force':
            force = False
    from libsw import build_queue, build_index
    queue = build_queue.new_queue(force)
    build_index.Index().populate_builders(queue)
    if queue.failed():
        print("One or more builds failed.")
    elif queue.run() == 0:
        print("All software is already up-to-date.")
index.register_command('update', _update)
index.register_command('upgrade', _update) # for yum/dnf habits :)

def _checkupdate():
    from libsw import build_queue, build_index
    queue = build_queue.new_queue(False)
    build_index.Index().populate_builders(queue)
    update_list = queue.run_check()
    if len(update_list) == 0:
        print("All software is already up-to-date.")
    else:
        for slug, status in update_list:
            if status == 'update':
                print(slug + ' requires an update')
            elif status == 'depend':
                print(slug + ' requires a rebuild following updates to dependencies')
index.register_command('checkupdate', _checkupdate)
index.register_command('check-update', _checkupdate) # for apt habits :)

def _run(first, more):
    from libsw import build_queue, build_index
    slug_list = []
    if not first:
        slug_list = build_index.select_slugs('Select software to build')
    else:
        slug_list.append(first)
        if more:
            for slug in more:
                slug_list.append(slug)

    queue = build_queue.TargetedQueue(slug_list)
    build_index.populate_slug_list(queue, slug_list)
    build_index.populate_dependant_builders(queue)
    # index.populate_builders(queue)
    if queue.run() == 0:
        print("Unable to build " + slug_list[0])
index.register_command('run', _run)

def _list():
    from libsw import build_index
    slug_list = build_index.enabled_slugs()
    for slug in slug_list:
        print(slug)
index.register_command('list', _list)

def _log(slug):
    from libsw import build_index
    if not slug:
        slug = build_index.select_slug('Select a package to view')
    slug = slug.lower()
    if not build_index.view_log(slug):
        print('No log file found for "' + slug + '".')
index.register_command('log', _log)

def _freeze(slug):
    from libsw import builder, build_index
    slug_list = build_index.enabled_slugs()
    if not slug:
        slug = build_index.select_slug('Select a package to freeze')
    if slug not in slug_list:
        print('Not a valid slug')
    else:
        if builder.freeze(slug):
            print('Froze ' + slug)
        else:
            print(slug + ' already frozen')
index.register_command('freeze', _freeze)

def _unfreeze(slug):
    from libsw import builder, build_index
    if not slug:
        slug = build_index.select_slug('Select a package to unfreeze')
    if builder.unfreeze(slug):
        print(slug + ' is no longer frozen')
    else:
        print(slug + ' was not in the frozen list')
index.register_command('unfreeze', _unfreeze)
index.register_command('thaw', _unfreeze)

def _listfreeze():
    from libsw import builder
    slug_list = builder.list_frozen()
    if len(slug_list) > 0:
        print()
        for slug in slug_list:
            print(slug)
        print()
    else:
        print('Nothing is frozen')
index.register_command('listfreeze', _listfreeze)
index.register_command('listfrozen', _listfreeze)

def _version(slug):
    from libsw import build_index
    if not slug:
        slug = build_index.select_slug("Select a package to print it's version")
    slug = slug.lower()
    builder = build_index.get_builder(slug)
    print(builder.version_reference())
index.register_command('version', _version)

def _install_prebuilt(slug, more):
    if not slug:
        print('Please specify slug being installed')
    if not more:
        print('Please specify version being installed')
    from libsw import build_index, logger
    if not slug:
        slug = build_index.select_slug("Select a package to (re)install it")
    slug = slug.lower()
    builder = build_index.get_builder(slug)
    builder.source_version = more[0]
    with open(builder.log_name(), 'w+') as log_output:
        log = logger.Log(log_output)
        builder.install(log)
index.register_command('installprebuilt', _install_prebuilt)
index.register_command('install-prebuilt', _install_prebuilt)