#!/usr/bin/env python3

import os

from libsw import settings, builder

default_failed_file = settings.get('install_path') + 'etc/build-failures'
debug = True

class BuildQueue():
    """
    A list of builders that can be built in a batch. Generally all
    depenencies of listed software is also listed. The build queue, when
    run, will only build missing and outdated software.
    """
    def __init__(self, failed_file=default_failed_file):
        self.queue = []
        self.failed_file = failed_file
        self.failure_cache = False

    def set_failed_file(self, failed_file):
        self.failed_file = failed_file
        self.failure_cache = False
        self.reset_statuses()

    def append(self, builder):
        """
        Add a builder to the queue regardless of weather or not is alread in the
        queue.

        Args:
            builder - The builder to add
        """
        status = ''
        self.queue.append([builder, status])

    def append_missing(self, builder):
        """
        Add a builder to the queue only if it is not alread in the queue.

        Args:
            builder - The builder to add
        """
        for b,status in self.queue:
            if b.slug == builder.slug:
                return False
        self.append(builder)
        return True

    def populate_dependancy_tree(self):
        for builder, status in self.queue:
            builder.dependants = []
        for builder, status in self.queue:
            for test_builder, test_status in self.queue:
                if builder.slug in test_builder.dependencies():
                    builder.dependants.append(test_builder)

    def in_failed_state(self, slug):
        """
        Check if a builder is marked as having failed a build.

        Args:
            slug - The slug name of the software package to check
        """
        self.failure_cache
        if self.failure_cache == False:
            self.failure_cache = []
            if os.path.exists(self.failed_file):
                with open(self.failed_file) as fail_list:
                    for fail in fail_list:
                        if len(fail) > 0:
                            self.failure_cache.append(fail.strip())
        for fail in self.failure_cache:
            if slug == fail:
                return True
        return False

    def _write_failed_file(self):
        """
        Write the list of failed software slugs to the configuration file.
        """
        if self.failure_cache != False:
            with open(self.failed_file, 'w+') as fail_list:
                for slug in self.failure_cache:
                    fail_list.write(slug + '\n')

    # def get_ordered_builders(self):
    def optimize(self):
        """
        Get an array of builders ordered so that all packages are preceded by their
        dependencies.
        """
        source_list = []
        target_list = []
        # for builder_tuple in self.queue:
        #     source_list.append(builder_tuple)
        source_list.extend(self.queue)
        old_length = 0
        current_length = len(source_list)
        # print('Len: ' + str(current_length))
        while len(source_list) > 0 and len(source_list) != old_length:
            old_length = current_length
            for build_tuple in source_list:
                deps = build_tuple[0].dependencies()
                satisfied = True
                for dep in deps:
                    found_dep = False
                    for builder, status in target_list:
                        if builder.slug == dep:
                            found_dep = True
                            break
                    if not found_dep:
                        satisfied = False
                if satisfied:
                    target_list.append(build_tuple)
            for build_tuple in target_list:
                if build_tuple in source_list:
                    source_list.remove(build_tuple)
            current_length = len(source_list)
        if len(source_list) > 0:
            print('Error: Dependency loop detected.')
            return False
        self.queue = target_list
        return target_list

    def run_check(self):
        """
        Check for updates for all installable software and print the results but
        do not install anthing.
        """
        self.reset_statuses()
        rebuild_list = []
        for i in range(len(self.queue)):
            builder, status = self.queue[i]
            status = self.live_status(builder)
            if status == 'pass':
                pass
            elif status == 'ready':
                rebuild_list.append([builder.slug, 'update'])
            elif status == 'waiting':
                rebuild_list.append([builder.slug, 'depend'])
        return rebuild_list

    def run(self):
        """
        Check for updates for all installable software and install any missing
        sowftware along with any software with an avaliable update.
        """
        self.count = 0
        self.reset_statuses()
        # for i in range(len(self.queue)):
        #     builder, status = self.queue[i]
        #     status = self.live_status(builder)
        #     self.queue[i] = builder, status
        # self._write_failed_file()
        for i in range(len(self.queue)):
            builder, status = self.queue[i]
            status = self.live_status(builder)
            if status == 'pass':
                pass
            else:
                if status == 'ready':
                    # add the current build to the failed file and only remove
                    # it after a successful build so that if Site Wrangler or
                    # the system crashes, the build starts up where it left off
                    # on next run
                    if not self.in_failed_state(builder.slug):
                        self.failure_cache.append(builder.slug)
                        #TODO mark dependents as failed in the failure_cache
                        self._write_failed_file()
                    success, log = builder.build()
                    if success:
                        status = 'done'
                        self.count += 1
                        self.failure_cache.remove(builder.slug)
                        self._write_failed_file()
                    else:
                        status = 'failed'
            self.queue[i] = builder, status
        return self.count

    def find(self, slug):
        """
        Fetch a builder from the queue.

        Args:
            slug - The slug name of the builder to return
        """
        for builder, status in self.queue:
            if builder.slug == slug:
                return builder
        return False

    def entry(self, slug):
        """
        Fetch a builder from the queue along with it's build status.

        Args:
            slug - The slug name of the builder to return
        """
        for builder, status in self.queue:
            if builder.slug == slug:
                return builder, status
        return False, False

    def mark_dependents_failed(self, builder):
        """
        Mark all builders that are dependent upon a builder as failed.

        Args:
            builder - The failed builder that needs dependent software marked as
                failed
        """
        write = False
        if not self.in_failed_state(builder.slug):
            self.failure_cache.append(builder.slug)
            write = True
        #TODO fix this so that it correctly walks the dependency tree
        # builder.dependencies()

        for other_builder in self.dependents:
            child_wrote = mark_dependents_failed(dep_builder)
            if child_wrote:
                write = False

        # for other_builder in self.queue:
        #     if builder.slug in other_builder.dependencies():
        #         child_wrote = mark_dependents_failed(dep_builder)
        #         if child_wrote:
        #             write = False

        # for dep in dependencies:
        #     dep_builder = self.find(dep)
        #     if dep_builder:
        #         child_wrote = mark_dependents_failed(dep_builder)
        #         if child_wrote:
        #             write = False
        if write:
            self._write_failed_file()
        return write

    def failed(self):
        """
        Returns True if any builder is in a failed state.
        """
        for builder, status in self.queue:
            if status == 'failed':
                return True
        return False

    def incomplete_count(self):
        """
        Returns the number of builders that are still set to install.
        """
        count = 0
        for builder, status in self.queue:
            if status != 'done':
                count += 1
        return count

    def reset_statuses(self):
        """
        Setup the builders for a fresh queue run by setting initial build
        statuses.
        """
        for i in range(len(self.queue)):
            builder, status = self.queue[i]
            status = ''
            if self.in_failed_state(builder.slug):
                if debug:
                    print('Marking ' + builder.slug + ' for build due to previous failure.')
                status = 'waiting'
            self.queue[i] = builder, status

    def live_status(self, builder, level=0):
        """
        Recalculate the status of a builder by checking it's dependencies.

        Args:
            builder - The builder to check
            level - The recursive depth level the status check is in
        """
        status = 'missing'
        for b, s in self.queue:
            if b is builder:
                status = s
        if status == '' or status == 'waiting':
            if status == '' and not builder.update_needed():
                status = 'pass'
            else:
                status = 'ready'
            deps = builder.dependencies()
            if len(deps) > 0:
                for slug in deps:
                    dep_builder, dep_status = self.entry(slug)
                    if dep_status == False:
                        print('Unable to find package "' + slug + '" needed for "' + builder.slug + '"') # TODO replace with logger
                        return 'failed'
                    dep_status = self.live_status(dep_builder, level + 1)
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

class RebuildQueue(BuildQueue):
    """
    A build queue that rebuilds all software regardless of update status.
    """
    def reset_statuses(self):
        for i in range(len(self.queue)):
            builder, status = self.queue[i]
            self.queue[i] = builder, 'waiting'

class TargetedQueue(BuildQueue):
    """
    A build queue that rebuilds one software packages and any software that
    depends on it. This is needed when a change is made to a build configuration.
    """
    def __init__(self, target_list):
        super().__init__()
        self.target_list = target_list

    def reset_statuses(self):
        for i in range(len(self.queue)):
            builder, status = self.queue[i]
            if builder.slug in self.target_list:
                self.queue[i] = builder, 'waiting'
            else:
                self.queue[i] = builder, 'pass'
        self.run_backwards_depenencies()

    def run_backwards_depenencies(self):
        count = 1
        while count > 0:
            count = 0
            for queue_item in self.queue:
                if queue_item[1] == 'waiting':
                    for i in range(len(self.queue)):
                        builder, status = self.queue[i]
                        dependencies = builder.dependencies()
                        if status != 'waiting' and queue_item[0].slug in dependencies:
                            count += 1
                            self.queue[i] = builder, 'waiting'

def new_queue(force=False):
    """
    A convenience function to initialize either a BuildQueue or RebuildQueue.
    """
    if force:
        return RebuildQueue()
    else:
        return BuildQueue()
