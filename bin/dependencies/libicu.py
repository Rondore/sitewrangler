from libsw import dependency, dependency_index

class LibIcuDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libicu')

    def get_system_name(self) -> str:
        return 'libicu76'

    def get_dev_system_name(self) -> str:
        return 'libicu-dev'
    
dependency_index.Index().register_dependency(LibIcuDependency())