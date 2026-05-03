from libsw import dependency, dependency_index

class LibGmpDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libgmp')

    def get_system_name(self) -> str:
        return 'libgmp10'

    def get_dev_system_name(self) -> str:
        return 'libgmp-dev'
    
dependency_index.Index().register_dependency(LibGmpDependency())