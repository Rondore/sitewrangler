from libsw import dependency, dependency_index

class LibWebpmuxDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libwebpmux')

    def get_system_name(self) -> str:
        return 'libwebpmux3'

    def get_dev_system_name(self) -> str:
        return 'libwebp-dev'
    
dependency_index.Index().register_dependency(LibWebpmuxDependency())