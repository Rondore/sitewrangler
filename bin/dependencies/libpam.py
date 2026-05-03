from libsw import dependency, dependency_index

class LibPamDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libpam')

    def get_system_name(self) -> str:
        return 'libpam0g'

    def get_dev_system_name(self) -> str:
        return 'libpam0g-dev'
    
dependency_index.Index().register_dependency(LibPamDependency())