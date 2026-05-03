from libsw import dependency, dependency_index

class LibZipDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libzip')

    def get_system_name(self) -> str:
        return 'libzip5'

    def get_dev_system_name(self) -> str:
        return 'libzip-dev'
    
dependency_index.Index().register_dependency(LibZipDependency())