#!/usr/bin/env python3

import os

from libsw import settings, builder, container

default_failed_file = settings.get('install_path') + 'etc/build-failures'
debug = settings.get('debug_build_queue')

type Target = builder.AbstractBuilder | container.ContainerImage

class BuildQueue():
    """
    A list of targets that can be built in a batch. Generally all
    depenencies of listed software is also listed. The build queue, when
    run, will only build missing and outdated software.
    """
    def __init__(self, failed_file=default_failed_file):
        self.queue: list[tuple[Target, str]] = []
        self.failed_file = failed_file
        self.failure_cache = False

    def set_failed_file(self, failed_file):
        self.failed_file = failed_file
        self.failure_cache = False
        self.reset_statuses()

    def append(self, target: Target):
        """
        Add a target to the queue regardless of weather or not is alread in the
        queue.

        Args:
            target - The target to add
        """
        status = ''
        self.queue.append([target, status])

    def append_missing(self, target: Target) -> bool:
        """
        Add a target to the queue only if it is not alread in the queue.

        Args:
            target - The target to add
        """
        for b,status in self.queue:
            if b.slug == target.slug:
                return False
        self.append(target)
        return True

    def populate_dependancy_tree(self):
        for target, status in self.queue:
            target.dependants = []
        for target, status in self.queue:
            for test_target, test_status in self.queue:
                if target.slug in test_target.dependencies():
                    target.dependants.append(test_target)

    def in_failed_state(self, slug: str) -> bool:
        """
        Check if a target is marked as having failed a build.

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

    def optimize(self) -> list[tuple[Target, str]]:
        """
        Get an array of targets ordered so that all packages are preceded by their
        dependencies.
        """
        source_list = []
        target_list: list[tuple[Target, str]] = []
        # for target_tuple in self.queue:
        #     source_list.append(target_tuple)
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
                    for target, status in target_list:
                        if target.slug == dep:
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

    def run_check(self) -> tuple[str, str]:
        """
        Check for updates for all installable software and print the results but
        do not install anthing.
        """
        self.reset_statuses()
        rebuild_list: tuple[str, str] = []
        for i in range(len(self.queue)):
            target, status = self.queue[i]
            status = self.live_status(target)
            if status == 'pass':
                pass
            elif status == 'ready':
                rebuild_list.append([target.slug, 'update'])
            elif status == 'waiting':
                rebuild_list.append([target.slug, 'depend'])
        return rebuild_list

    def run(self) -> int:
        """
        Check for updates for all installable software and install any missing
        sowftware along with any software with an avaliable update.
        """
        self.count = 0
        self.reset_statuses()
        # for i in range(len(self.queue)):
        #     target, status = self.queue[i]
        #     status = self.live_status(target)
        #     self.queue[i] = target, status
        # self._write_failed_file()
        for i in range(len(self.queue)):
            target, status = self.queue[i]
            status = self.live_status(target)
            if status == 'pass':
                pass
            else:
                if status == 'ready':
                    # add the current build to the failed file and only remove
                    # it after a successful build so that if Site Wrangler or
                    # the system crashes, the build starts up where it left off
                    # on next run
                    if not self.in_failed_state(target.slug):
                        self.failure_cache.append(target.slug)
                        #TODO mark dependents as failed in the failure_cache
                        self._write_failed_file()
                    success, log = target.build()
                    if success:
                        status = 'done'
                        self.count += 1
                        self.failure_cache.remove(target.slug)
                        self._write_failed_file()
                    else:
                        status = 'failed'
            self.queue[i] = target, status
        return self.count

    def find(self, slug) -> Target | False:
        """
        Fetch a target from the queue.

        Args:
            slug - The slug name of the target to return
        """
        for target, status in self.queue:
            if target.slug == slug:
                return target
        return False

    def entry(self, slug) -> tuple[Target, str] | tuple[False, False]:
        """
        Fetch a target from the queue along with it's build status.

        Args:
            slug - The slug name of the target to return
        """
        for target, status in self.queue:
            if target.slug == slug:
                return target, status
        return False, False

    def mark_dependents_failed(self, target: Target) -> bool:
        """
        Mark all targets that are dependent upon a builder as failed.

        Args:
            target - The failed target that needs dependent software marked as
                failed
        """
        write = False
        if not self.in_failed_state(target.slug):
            self.failure_cache.append(target.slug)
            write = True
        #TODO fix this so that it correctly walks the dependency tree
        # target.dependencies()

        for other_target in self.dependents:
            child_wrote = self.mark_dependents_failed(other_target)
            if child_wrote:
                write = False

        # for other_target in self.queue:
        #     if target.slug in other_target.dependencies():
        #         child_wrote = self.mark_dependents_failed(other_target)
        #         if child_wrote:
        #             write = False

        # for dep in dependencies:
        #     dep_target = self.find(dep)
        #     if dep_target:
        #         child_wrote = self.mark_dependents_failed(dep_target)
        #         if child_wrote:
        #             write = False
        if write:
            self._write_failed_file()
        return write

    def failed(self) -> bool:
        """
        Returns True if any target is in a failed state.
        """
        for target, status in self.queue:
            if status == 'failed':
                return True
        return False

    def incomplete_count(self) -> int:
        """
        Returns the number of targets that are still set to install.
        """
        count = 0
        for target, status in self.queue:
            if status != 'done':
                count += 1
        return count

    def reset_statuses(self):
        """
        Setup the targets for a fresh queue run by setting initial build
        statuses.
        """
        for i in range(len(self.queue)):
            target, status = self.queue[i]
            status = ''
            if self.in_failed_state(target.slug):
                print('Marking ' + target.slug + ' for build due to previous action.')
                status = 'waiting'
            self.queue[i] = target, status

    def live_status(self, target, level=0) -> str:
        """
        Recalculate the status of a target by checking it's dependencies.

        Args:
            target - The target to check
            level - The recursive depth level the status check is in
        """
        dmsg = 'Checking '
        for i in range(level):
            dmsg += ' '
        dmsg += target.slug + ': '
        if debug or level == 0:
            print(dmsg, end='', flush=True)

        status = 'missing'
        for b, s in self.queue:
            if b is target:
                status = s
        if status == '' or status == 'waiting':
            if not settings.use_containers and status == '' and not target.update_needed():
                status = 'pass'
            else:
                status = 'ready'
            deps = target.dependencies()
            if len(deps) > 0:
                for slug in deps:
                    dep_target, dep_status = self.entry(slug)
                    if dep_status == False:
                        print('Unable to find package "' + slug + '" needed for "' + target.slug + '"') # TODO replace with logger
                        return 'failed'
                    dep_status = self.live_status(dep_target, level + 1)
                    if dep_status == 'failed' or dep_status == 'missing':
                        return 'failed'
                    elif dep_status == 'waiting' or dep_status == 'ready':
                        status = 'waiting'
                    elif dep_status == 'done':
                        if status != 'waiting':
                            status = 'ready'

        if debug or level == 0:
            print(status, flush=True)
        return status
    
    def remove(self, value):
        if isinstance(object, str):
            for pair in self.queue:
                child, status = pair
                if child.slug == value:
                    self.queue.remove(pair)
                    return
        else:
            for pair in self.queue:
                child, status = pair
                if child == value:
                    self.queue.remove(pair)
                    return

class RebuildQueue(BuildQueue):
    """
    A build queue that rebuilds all software regardless of update status.
    """
    def reset_statuses(self):
        for i in range(len(self.queue)):
            target, status = self.queue[i]
            self.queue[i] = target, 'waiting'

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
            target, status = self.queue[i]
            if target.slug in self.target_list:
                self.queue[i] = target, 'waiting'
            else:
                self.queue[i] = target, 'pass'
        self.run_backwards_depenencies()

    def run_backwards_depenencies(self):
        count = 1
        while count > 0:
            count = 0
            for queue_item in self.queue:
                if queue_item[1] == 'waiting':
                    for i in range(len(self.queue)):
                        target, status = self.queue[i]
                        dependencies = target.dependencies()
                        if status != 'waiting' and queue_item[0].slug in dependencies:
                            count += 1
                            self.queue[i] = target, 'waiting'

def new_queue(force=False):
    """
    A convenience function to initialize either a BuildQueue or RebuildQueue.
    """
    if force:
        return RebuildQueue()
    else:
        return BuildQueue()
