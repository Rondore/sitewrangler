from libsw import dependency, dependency_index

class LibPslDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libpsl')

    def get_system_name(self) -> str:
        return 'libpsl5'

    def get_dev_system_name(self) -> str:
        return 'libpsl-dev'
    
dependency_index.Index().register_dependency(LibPslDependency())