from libsw import dependency, dependency_index

class LibMpcDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libmpc')

    def get_system_name(self) -> str:
        return 'libmpc3'

    def get_dev_system_name(self) -> str:
        return 'libmpc-dev'
    
dependency_index.Index().register_dependency(LibMpcDependency())