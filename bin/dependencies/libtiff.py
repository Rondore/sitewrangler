from libsw import dependency, dependency_index

class LibTiffDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libtiff')

    def get_system_name(self) -> str:
        return 'libtiff6'

    def get_dev_system_name(self) -> str:
        return 'libtiff-dev'
    
dependency_index.Index().register_dependency(LibTiffDependency())