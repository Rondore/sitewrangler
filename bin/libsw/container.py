#!/usr/bin/env python3

from abc import ABC, abstractmethod
import shutil
from libsw import email, logger, settings, builder, build_container, dependency_index, build_index
import os
from typing import Literal
import subprocess

default_base_image = 'debian:trixie'

dep_index = dependency_index.Index()

thread_count = subprocess.getoutput('nproc')

build_env: list[tuple[str, str]] = [
    ['LD_LIBRARY_PATH', '/opt/sitewrangler/usr/lib64:/opt/sitewrangler/usr/lib'],
    ['LDFLAGS', '-L/opt/sitewrangler/usr/lib64/ -L/opt/sitewrangler/usr/lib/'],
    ['CPPFLAGS', '-I/opt/sitewrangler/usr/include/'],
    ['PKG_CONFIG_PATH', '/opt/sitewrangler/usr/lib64/pkgconfig/:/opt/sitewrangler/usr/lib/pkgconfig/']
]

container_build_env: list[tuple[str, str]] = [
    ['MAKEFLAGS', '-j' + thread_count]
]

debug_container_logic = False
def print_container_debug(output: str):
    if debug_container_logic:
        print(output)

class AbstractContainerBuildSystem(ABC):

    @abstractmethod
    def get_build_filename(self) -> str:
        pass

    @abstractmethod
    def get_compose_filename(self) -> str:
        pass

    @abstractmethod
    def get_image_prefix(self) -> str:
        pass

    @abstractmethod
    def get_build_command(self, tag, source_directory) -> list[str]:
        pass

class PodmanBuildSystem(AbstractContainerBuildSystem):

    def get_build_filename(self) -> str:
        return 'Containerfile'

    def get_compose_filename(self) -> str:
        return 'podman-compose.yaml'

    def get_image_prefix(self) -> str:
        return 'localhost/sitewrangler/'

    def get_build_command(self, tag, source_directory) -> list[str]:
        command = ['podman', 'build', source_directory, '--net=host']
        for env in container_build_env:
            command.append(f'--env={env[0]}={env[1]}')
        command.append('-t')
        command.append(tag)
        return command

class DockerBuildSystem(AbstractContainerBuildSystem):

    def get_build_filename(self) -> str:
        return 'Dockerfile'

    def get_compose_filename(self) -> str:
        return 'docker-compose.yaml'

    def get_image_prefix(self) -> str:
        return 'sitewrangler/'

    def get_build_command(self, tag, source_directory) -> list[str]:
        command = ['docker', 'build', source_directory]
        for env in container_build_env:
            command.append('--build-arg')
            command.append(f'{env[0]}="{env[1]}"')
        command.append('-t')
        command.append(tag)
        return command
    
build_system = False
def get_container_build_system() -> AbstractContainerBuildSystem:
    global build_system
    if(not build_system):
        system_name = settings.get('build_system')
        if system_name == 'docker':
            build_system = DockerBuildSystem()
        else:
            build_system = PodmanBuildSystem()
    return build_system

container_cache = dict()
def get_container(slug: str) -> False | ContainerImage:
    global container_cache
    image = False
    try:
        image = container_cache[slug]
    except KeyError:
        builder = build_index.get_builder(slug)
        if builder:
            image = ContainerImage(builder)
            container_cache[slug] = image
    return image

def get_recursive_dependencies(builder: builder.AbstractBuilder) -> list[builder.AbstractBuilder]:
    dependencies = []
    dependency_slugs = []
    for slug in builder.dependencies():
        if slug not in dependency_slugs:
            builder = build_index.get_builder(slug)
            if builder:
                dependency_slugs.append(slug)
                dependencies.append(builder)
                child_dependencies = get_recursive_dependencies(builder)
                for child in child_dependencies:
                    if child.slug not in dependency_slugs:
                        dependency_slugs.append(child.slug)
                        dependencies.append(child)
    return dependencies
        
def get_recursive_system_dependencies(builder: builder.AbstractBuilder) -> list[str]:
    builders = get_recursive_dependencies(builder)
    builders.append(builder)
    system_dependencies = []
    for build in builders:
        for name in build.system_dependencies():
            if name not in system_dependencies:
                system_dependencies.append(name)
    return system_dependencies

def get_optimal_base_image(builders: list[builder.AbstractBuilder]) -> tuple[builder.AbstractBuilder, list[builder.AbstractBuilder]] | tuple[False, False]:
    length = len(builders)
    if length == 0:
        return False, False
    elif length == 1:
        return builders[0], get_recursive_dependencies(builders[0])
    
    optimal = False
    optimal_dependencies = []
    for builder in builders:
        if not optimal:
            optimal = builder
            optimal_dependencies = get_recursive_dependencies(optimal)
            continue
        if builder in optimal_dependencies:
            continue
        builder_deps = get_recursive_dependencies(builder)
        if (optimal in builder_deps) or (len(builder_deps) > len(optimal_dependencies)):
            optimal = builder
            optimal_dependencies = builder_deps
    return optimal, optimal_dependencies

def sort_builders_by_prereq(builders: list[builder.AbstractBuilder]) -> list[builder.AbstractBuilder]:
    sorted: list[builder.AbstractBuilder] = []
    for builder in builders:
        insert_index = -1
        for dep in builder.dependencies():
            try:
                index = sorted.index(dep)
                if index > insert_index:
                    insert_index = index
            except ValueError:
                pass
        sorted.insert(insert_index + 1, builder)
    return sorted

def get_image_slug(full_name: str) -> str:
    return full_name.split('/')[-1].split(':')[0]

def folder_has_content(path: str) -> bool:
    if not os.path.exists(path):
        return False
    return len(os.listdir(path)) > 0

class ContainerImage:
    """
    An abstract class to build docker containers.
    """
    def __init__(self, builder: builder.AbstractBuilder):
        self.slug = builder.slug
        header = '=== ' + self.slug + ' ==='
        print_container_debug('=' * len(header))
        print_container_debug(header)
        print_container_debug('=' * len(header))
        self.builder = builder
        self.copy_commands: list[tuple[str, str]] = []
        dependency_builders = get_recursive_dependencies(builder)
        print_container_debug('=== Dependencies ===')
        for builder in dependency_builders:
            print_container_debug(builder.slug)
        print_container_debug("")

        base_image_pool: list[builder.AbstractBuilder] = []
        for builder in dependency_builders:
            if builder.standalone_container():
                base_image_pool.append(builder)
        print_container_debug('=== Base Image Pool ===')
        for builder in base_image_pool:
            print_container_debug(builder.slug)
        print_container_debug("")

        # Find the base image
        base_image_builder, base_dependencies = get_optimal_base_image(base_image_pool)
        if base_image_builder:
            self.base_image = get_container_build_system().get_image_prefix() + base_image_builder.slug
        else:
            self.base_image = default_base_image
        print_container_debug('=== Base Image ===')
        print_container_debug(self.base_image)
        print_container_debug("")

        # Find images that will be copied into the build and final images
        self.added_images: list[builder.AbstractBuilder] = []
        self.already_in_base_image: list[builder.AbstractBuilder] = []
        for image in base_image_pool:
            if image != base_image_builder:
                if image.slug in base_image_builder.dependencies():
                    self.already_in_base_image.append(image)
                else:
                    self.added_images.append(image)
        print_container_debug('=== Added Images ===')
        for image in self.added_images:
            print_container_debug(image.slug)
        print_container_debug("")

        # Find software that will need to be compiled as part of this image build
        self.included_builders: list[builder.AbstractBuilder] = []
        if base_dependencies:
            for builder in dependency_builders:
                if builder not in base_dependencies and builder not in base_image_pool:
                    self.included_builders.append(builder)
        for slug in self.builder.get_extra_includes():
            builder = build_index.get_builder(slug)
            if builder:
                self.included_builders.append(builder)
        self.included_builders = sort_builders_by_prereq(self.included_builders)
        print_container_debug('=== Included Software ===')
        for builder in self.included_builders:
            print_container_debug(builder.slug)
        print_container_debug("")

        # Find system packages that will need to be installed in the final image (apt install)
        unnecessary = []
        if base_image_builder:
            unnecessary = get_recursive_system_dependencies(base_image_builder)
        self.system_dependencies: list[str] = self.builder.system_dependencies()
        for builder in dependency_builders:
            if builder != base_image_builder:
                for dep in get_recursive_system_dependencies(builder):
                    if dep not in unnecessary and dep not in self.system_dependencies:
                        self.system_dependencies.append(dep)
        self.system_dependencies = dep_index.list_dependent_names(self.system_dependencies)
        print_container_debug('=== System Packages ===')
        for name in self.system_dependencies:
            print_container_debug(name)
        print_container_debug("")

    def get_base_image(self):
        """
        Get the name of the base container image. Names starting with a plus sign
        refer to another image built by Site Wrangler.
        """
        return default_base_image

    def log_name(self):
        name = settings.get('install_path') + 'var/log/build/' + self.slug + '.log'
        return name
    
    def build(self):
        print('Building ' + self.slug)
        success = False
        logfile = self.log_name()
        logdir = os.path.dirname(logfile)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        with open(logfile, 'w+') as open_log:
            log = logger.Log(open_log)
            self.compile_build_file()
            for source, destination in self.copy_commands:
                target_path = self.get_build_file_folder() + '/' + destination
                if not os.path.exists(target_path):
                    shutil.copytree(source, target_path)
            tag = build_system.get_image_prefix() + self.slug
            build_command = build_system.get_build_command(tag, self.get_build_file_folder())
            log.log(f'Building conainer image for {self.slug}')
            retval = log.run(build_command)
            success = retval == 0

        if success:
            for package in self.included_builders:
                package.cleanup_old_versions(log)
            self.builder.cleanup_old_versions(log)
            if settings.get_bool('email_admin_on_build_success'):
                email.send_admin_log_clip('Build succeeded for ' + self.slug, logfile)
        else:
            email.send_admin_logfile('Build failed for  ' + self.slug, logfile)
        return success, logfile

    def get_builder_image(self) -> str | Literal[False]:
        return build_container.default_builder_image_slug
    
    def craft_compile_command(self, log: logger.Log) -> list[str]:
        output = []
        capture = logger.CaptureCommandsLog()
        for builder in self.included_builders:
            builder.run_fetch(log)
            capture.run(f"cd \"/opt/sitewrangler/usr/src/{builder.slug}/\"")
            build_env = builder.get_build_env()
            for key in build_env:
                value = build_env[key]
                capture.run(f'export {key}="{value}"')
            builder.build(capture, True)
        self.builder.run_fetch(log)
        capture.run(f"cd \"/opt/sitewrangler/usr/src/{self.builder.slug}/\"")
        build_env = self.builder.get_build_env()
        for key in build_env:
            value = build_env[key]
            capture.run(f'export {key}="{value}"')
        self.builder.build(capture, True)
        prefix = "RUN "
        for command in capture.commands:
            output.append(prefix + command + " && \\\n")
            prefix = "    "
        output.append(prefix + "rm -rf /opt/sitewrangler/usr/src\n")
        return output
    
    def compile_build_file(self) -> str:
        """
        Create the Containerfile/Dockerfile needed to build the container image.
        """
        build_log = logger.Log()
        build_sys = get_container_build_system()
        image_prefix = build_sys.get_image_prefix()
        container_build_file = self.get_build_file_path()
        os.makedirs(self.get_build_file_folder(), exist_ok=True)
        compile_command = self.craft_compile_command(build_log)
        base_image_name = ''
        if self.base_image:
            base_image_name = get_image_slug(self.base_image)
        with open(container_build_file, 'w+') as output:
            for image in self.added_images:
                output.write(f"FROM {image_prefix}{image.slug} AS {image.slug}\n")
            if self.base_image and (len(self.added_images) == 0 or self.base_image != default_base_image):
                output.write(f"FROM {self.base_image} AS {base_image_name}\n")

            builder_image = self.get_builder_image()
            if builder_image:
                output.write(f"FROM {image_prefix}{builder_image} AS builder\n\n")

                #TODO we probably need to add commands to write version numbers to a file to force rebuilds on versions changes
                if self.base_image and self.base_image != default_base_image:
                    output.write(f"COPY --from={base_image_name} /opt/sitewrangler/usr/ /opt/sitewrangler/usr/\n")
            for image in self.added_images:
                output.write(f"COPY --from={image.slug} /opt/sitewrangler/usr/ /opt/sitewrangler/usr/\n")

            for builder in self.included_builders:
                path = builder.source_dir()
                # if folder_has_content(path):
                build_log.log('adding ' + builder.slug)
                ver_slug = builder.slug + '-' + builder.source_version
                self.copy_commands.append([builder.source_dir(), ver_slug])
                output.write(f"COPY \"./{ver_slug}\" \"/opt/sitewrangler/usr/src/{builder.slug}/\"\n")
                # endif
            path = self.builder.source_dir()
            # if folder_has_content(path):
            ver_slug = self.builder.slug + '-' + self.builder.source_version
            self.copy_commands.append([path, ver_slug])
            output.write(f"COPY \"./{ver_slug}\" \"/opt/sitewrangler/usr/src/{self.builder.slug}/\"\n")
            # endif

            for line in compile_command:
                output.write(line)

            output.write("\n")
            if builder_image:
                output.write(f"FROM {self.base_image}\n")
                output.write("COPY --from=builder /opt/sitewrangler/usr/ /opt/sitewrangler/usr/\n")
            output.write("RUN apt-get update -qq && \\\n")
            output.write("    apt-get upgrade -qq && \\\n")
            if len(self.system_dependencies) > 0:
                output.write("    apt-get install -qq \\\n")
                for sys_dep in self.system_dependencies:
                    output.write(f"    {sys_dep} \\\n")
                output.write("    && \\\n")
            output.write("    apt-get clean -qq\n")
            self.builder.add_container_config(output)
        return container_build_file
    
    def get_build_file_folder(self) -> str:
        path = settings.get('install_path')
        path += '/var/cache/container-build/'
        path += self.slug + '/'
        return path

    def get_build_file_path(self) -> str:
        build_system = get_container_build_system()
        return self.get_build_file_folder() + build_system.get_build_filename()

    def dependencies(self) -> list[str]:
        """
        Returns a list of slugs of the other software images this builder relies on.
        """
        deps = []
        if self.base_image != default_base_image:
            deps.append(self.base_image.split('/')[-1])
        deps.extend([builder.slug for builder in self.added_images])
        return deps

all_enabled_builders = False
def get_all_enabled_builders() -> list[builder.AbstractBuilder]:
    global all_enabled_builders
    if(not all_enabled_builders):
        all_enabled_builders = []
        from libsw import build_queue, build_index
        queue = build_queue.new_queue(False)
        populator = build_index.ContainerQueuePopulator(queue)
        populator.populate_enabled()
        populator.populate_dependant_builders()
        for builder, status in queue.queue:
            all_enabled_builders.append(builder)
    return all_enabled_builders

def find_enabled_builder(slug) -> builder.AbstractBuilder | Literal[False]:
    for builder in get_all_enabled_builders():
        if builder.slug == builder.slug:
            return builder
    return False
    
class CompilingImage(ContainerImage):
    def __init__(self):
        self.builder = build_container.BuildContainer()
        self.slug = self.builder.slug
        self.copy_commands: list[tuple[str, str]] = []
        self.base_image = default_base_image
        self.added_images: list[builder.AbstractBuilder] = []
        self.included_builders: list[builder.AbstractBuilder] = []
        self.system_dependencies: list[str] = []
        for package in get_all_enabled_builders():
            for dep in get_recursive_system_dependencies(package):
                if dep not in self.system_dependencies:
                    self.system_dependencies.append(dep)
        self.system_dependencies = dep_index.list_dependent_dev_names(self.system_dependencies)
        for name in [
            'gcc', 'make', 'automake', 'autoconf', 'build-essential', 'bison', 'flex', 'libtool', 'pkg-config', 'gcc-multilib'
        ]:
            self.system_dependencies.append(name)

    def get_base_image(self):
        return default_base_image

    def get_builder_image(self):
        return False

    def craft_compile_command(self, sorted_builders) -> list[str]:
        return []
    
def get_container_status(name: str) -> str:
    status = subprocess.getoutput(r"podman container inspect '" + name + r"' -f '{{.State.Status}}'", )
    if 'no such container' in status:
        status = 'missing'
    return status