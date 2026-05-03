from libsw import dependency, dependency_index

class LibPngDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libpng')

    def get_system_name(self) -> str:
        return 'libpng16-16t64'

    def get_dev_system_name(self) -> str:
        return 'libpng-dev'
    
dependency_index.Index().register_dependency(LibPngDependency())