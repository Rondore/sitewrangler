#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw build install [slug_list]  # Enable a software package and rund a build for it')
    print('sw build uninstall [slug_list]  # Remove a software package from the system')
    print('sw build disable [slug_list]  # Disable a software package but do not remove it from the system')
    print('sw build update [force]  # Update softare sources and build anthing that needs building')
    print('sw build checkupdate  # Check for updates to software sources and print a list of slugs that need updating')
    print('sw build list  # List all software slugs enabled on the system')
    print('sw build run [example]  # Rebuild a given (list of) software slug(s) and other software that depends on it')
    print('sw build log [example]  # Show the build log for the given software slug')
    print('sw build freeze [slug]  # Prevent a software package from updating to a newer version')
    print('sw build (unfreeze|thaw) [slug]  # Allow a software package to update to a newer version')
    print('sw build list(freeze|frozen)  # List software set to not update')
    print('sw build configure [slug]  # Print the configure command for a package')
index = command_index.CategoryIndex('build', _help)

def _update(force):
    if force:
        force = force.lower()
        if force != 'force':
            force = False
    from libsw import build_queue, build_index
    queue = build_queue.new_queue(force)
    build_index.populate_enabled(queue)
    build_index.populate_dependant_builders(queue)
    if queue.failed():
        print("One or more builds failed.")
    elif queue.run() == 0:
        print("All software is already up-to-date.")
index.register_command('update', _update)
index.register_command('upgrade', _update) # for yum/dnf habits :)

def _checkupdate():
    from libsw import build_queue, build_index
    queue = build_queue.new_queue(False)
    build_index.populate_enabled(queue)
    build_index.populate_dependant_builders(queue)
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

def _avaliable_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import build_index
    slug = args[0].lower()
    length = len(slug)
    slug_list = build_index.registered_slugs()
    for possible_slug in slug_list:
        if possible_slug[:length] == slug:
            print(possible_slug)

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
    if queue.run() == 0:
        print("Unable to build " + slug_list[0])
index.register_command('run', _run, autocomplete=_avaliable_autocomplete)

def _list():
    from libsw import build_index
    slug_list = build_index.registered_slugs()
    for slug in slug_list:
        print(slug)
index.register_command('list', _list)

def _installed_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import build_index
    slug = args[0].lower()
    length = len(slug)
    slug_list = build_index.get_installed()
    slug_list = build_index.get_list_with_dependants(slug_list)
    for possible_slug in slug_list:
        if possible_slug[:length] == slug:
            print(possible_slug)

def _log(slug):
    from libsw import build_index
    if not slug:
        slug = build_index.select_slug('Select a package to view')
    slug = slug.lower()
    if not build_index.view_log(slug):
        print('No log file found for "' + slug + '".')
index.register_command('log', _log, autocomplete=_installed_autocomplete)

def _freeze(slug):
    from libsw import builder, build_index
    slug_list = build_index.registered_slugs()
    if not slug:
        slug = build_index.select_slug('Select a package to freeze')
    if slug not in slug_list:
        print('Not a valid slug')
    else:
        if builder.freeze(slug):
            print('Froze ' + slug)
        else:
            print(slug + ' already frozen')

def _freeze_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import builder, build_index
    slug = args[0].lower()
    length = len(slug)
    slug_list = build_index.get_installed()
    slug_list = build_index.get_list_with_dependants(slug_list)
    frozen_list = builder.list_frozen()
    for possible_slug in slug_list:
        if possible_slug[:length] == slug:
            if possible_slug not in frozen_list:
                print(possible_slug)
index.register_command('freeze', _freeze, autocomplete=_freeze_autocomplete)

def _unfreeze(slug):
    from libsw import builder, build_index
    if not slug:
        slug = build_index.select_slug('Select a package to unfreeze')
    if builder.unfreeze(slug):
        print(slug + ' is no longer frozen')
    else:
        print(slug + ' was not in the frozen list')

def _unfreeze_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import build_index, builder
    slug = args[0].lower()
    length = len(slug)
    frozen_list = builder.list_frozen()
    for possible_slug in frozen_list:
        if possible_slug[:length] == slug:
            print(possible_slug)
index.register_command('unfreeze', _unfreeze, autocomplete=_unfreeze_autocomplete)
index.register_command('thaw', _unfreeze, autocomplete=_unfreeze_autocomplete)

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
index.register_command('version', _version, autocomplete=_installed_autocomplete)

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
index.register_command('installprebuilt', _install_prebuilt, autocomplete=_avaliable_autocomplete)
index.register_command('install-prebuilt', _install_prebuilt, autocomplete=_avaliable_autocomplete)

def _avaliable_new_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import build_index
    slug = args[0].lower()
    length = len(slug)
    slug_list = build_index.registered_slugs()
    installed_list = build_index.get_installed()
    installed_list = build_index.get_list_with_dependants(installed_list)
    for possible_slug in slug_list:
        if possible_slug in installed_list:
            continue
        if possible_slug[:length] == slug:
            print(possible_slug)

def _install(slug, more):
    from libsw import build_index, build_queue, file_filter
    slug_list = []
    if slug != False:
        slug = slug.lower()
        if build_index.get_builder(slug) != False:
            slug_list.append(slug)
        else:
            print('"' + slug + '" not found, skipping...')
    if more != False and len(more) > 0:
        for sub_slug in more:
            sub_slug = sub_slug.lower()
            if build_index.get_builder(sub_slug) != False:
                slug_list.append(sub_slug)
            else:
                print('"' + sub_slug + '" not found, skipping...')
    if len(slug_list) == 0:
        slug_list = build_index.select_slugs("Select software to install")
    count = 0
    for entry in slug_list:
        if build_index.enable_slug(entry):
            print('Enabled ' + entry)
            count += 1
        else:
            print(entry + ' already enabled (run "sw build update" to build)')
    if count > 0:
        suffix = 'packages'
        if count == 1:
            suffix = 'package'
        print('Enabled ' + str(count) + ' ' + suffix)
        queue = build_queue.new_queue(False)
        build_index.populate_slug_list(queue, slug_list)
        build_index.populate_dependant_builders(queue)
        queue.run()
        needs_rebuild = []
        for entry in slug_list:
            needs_rebuild.extend(build_index.get_dependant_upon(entry))
        if len(needs_rebuild) > 0:
            for rebuild in needs_rebuild:
                file_filter.AppendUnique(build_queue.default_failed_file, rebuild).run()
            print('Some packages must now be rebuilt. Run "sw build update" to build them.')
index.register_command('install', _install, autocomplete=_avaliable_new_autocomplete)

def _uninstall_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    from libsw import build_index
    slug = args[0].lower()
    length = len(slug)
    slug_list = build_index.registered_slugs()
    for possible_slug in slug_list:
        if possible_slug[:length] == slug:
            builder = build_index.get_builder(possible_slug)
            has_uninstall = hasattr(builder, 'uninstall') and callable(builder.uninstall)
            if has_uninstall:
                print(possible_slug)

def _uninstall(slug, more):
    from libsw import build_index, logger
    import os
    builder_list = []
    if slug != False:
        slug = slug.lower()
        builder = build_index.get_builder(slug)
        if builder != False:
            builder_list.append(builder)
        else:
            print('"' + slug + '" not found, skipping...')
    if more != False and len(more) > 0:
        for sub_slug in more:
            sub_slug = sub_slug.lower()
            builder = build_index.get_builder(sub_slug)
            if builder != False:
                builder_list.append(builder)
            else:
                print('"' + sub_slug + '" not found, skipping...')
    valid_builders = []
    for builder in builder_list:
        has_uninstall = hasattr(builder, 'uninstall') and callable(builder.uninstall)
        if(has_uninstall):
            valid_builders.append(builder)
        else:
            print('"' + builder.slug + '" does not have an uninstaller, skipping...')
    for builder in valid_builders:
        can_warn = hasattr(builder, 'uninstall_warnings') and callable(builder.uninstall_warnings)
        if can_warn:
            warnings = builder.uninstall_warnings()
            if warnings != False:
                print("Warning: " + warnings)
                if not input_util.confirm("Continue anyways?", False):
                    continue
        log = logger.Log()
        builder.uninstall(log)
        build_index.disable_slug(builder.slug)
        builder.cleanup_old_versions(log)
        os.remove(builder.log_name())
index.register_command('uninstall', _uninstall, autocomplete=_uninstall_autocomplete)

def _disable(slug, more):
    from libsw import build_index
    count = 0
    if slug != False:
        if build_index.disable_slug(slug):
            count += 1
        else:
            print('"' + slug + '" not found, skipping...')
    if more != False and len(more) > 0:
        for sub_slug in more:
            if build_index.disable_slug(sub_slug):
                count += 1
            else:
                print('"' + sub_slug + '" not found, skipping...')
    if count == 0:
        slug_list = build_index.select_slugs("Select software to disable")
        count = 0
        for entry in slug_list:
            if build_index.disable_slug(sub_slug):
                count += 1
            else:
                print('"' + entry + '" not expressly installed, skipping...')
    suffix = 'packages'
    if count == 1:
        suffix = 'package'
    print('Enabled ' + str(count) + ' ' + suffix)
index.register_command('disable', _disable, autocomplete=_installed_autocomplete)

def _configure(slug):
    if slug == False:
        print('Please provide a package name')
    else:
        from libsw import build_index, builder
        target = build_index.get_builder(slug)
        if target == False:
            print('Invalid package slug: ' + slug)
        else:
            command = builder.get_configure_command(target)
            print(' '.join(command))
index.register_command('configure', _configure)
index.register_command('conf', _configure)
