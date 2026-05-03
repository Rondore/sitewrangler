from libsw import dependency, dependency_index

class LibGdDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libgd')

    def get_system_name(self) -> str:
        return ' libgd3'

    def get_dev_system_name(self) -> str:
        return 'libgd-dev'
    
dependency_index.Index().register_dependency(LibGdDependency())