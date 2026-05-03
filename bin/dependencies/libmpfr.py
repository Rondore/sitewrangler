from libsw import dependency, dependency_index

class LibMpfrDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libmpfr')

    def get_system_name(self) -> str:
        return 'libmpfr6'

    def get_dev_system_name(self) -> str:
        return 'libmpfr-dev'
    
dependency_index.Index().register_dependency(LibMpfrDependency())