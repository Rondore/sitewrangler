import re
import requests
import subprocess

from libsw import builder, settings, version

build_path = settings.get('build_path')
binary_path = build_path + 'bin/gcc'

class GccBuilder(builder.AbstractArchiveBuilder):
    """A class to build GCC from source."""
    def __init__(self):
        super().__init__('gcc')

    def get_installed_version(self):
        about_text = subprocess.getoutput(builder.set_sh_ld + binary_path + ' --version')
        match = re.match(r'gcc \(GCC\) ([0-9a-z\.]*)', about_text)
        if match == None:
            return '0'
        return match.group(1)

    def get_updated_version(self):
        request = requests.get('https://mirrorservice.org/sites/sourceware.org/pub/gcc/releases/')
        regex = re.compile(r'<a href="gcc-([0-9a-z\.]*)')
        newest = '0.0.0'
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            ver = match.groups(0)[0]
            if(version.first_is_higher(ver, newest)):
                newest = ver
        return newest

    def get_source_url(self):
        return f'https://mirrorservice.org/sites/sourceware.org/pub/gcc/releases/gcc-{self.source_version}/gcc-{self.source_version}.tar.xz'
    
    def system_dependencies(self) -> list[str]:
        """
        Get a list of all system packages needed to run the built software (apt install)
        """
        return [
            'libgmp',
            'libmpc',
            'libmpfr',
            'binutils'
        ]
    
    # def add_container_config(self, output):
    #     output.write('COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt\n')
    #     output.write(r'ENV PATH="/opt/sitewrangler/usr/bin:${PATH}"' + '\n')
    #     output.write('ENV LD_LIBRARY_PATH="/opt/sitewrangler/usr/lib64:/opt/sitewrangler/usr/lib"\n')

    def standalone_container(self):
        return True

    def run_pre_config(self, log):
        log.run(['mkdir','../gcc-build'], env=self.get_build_env())
        log.run(['cd','../gcc-build'], env=self.get_build_env())

    def populate_config_args(self, log, command=['../gcc/configure']):
        return super().populate_config_args(log, command)