from libsw import dependency, dependency_index

class LibPcreDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libpcre')

    def get_system_name(self) -> str:
        return 'libpcre2-32-0'

    def get_dev_system_name(self) -> str:
        return 'libpcre2-dev'
    
dependency_index.Index().register_dependency(LibPcreDependency())