from libsw import dependency, dependency_index

class LibHeifDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libheif')

    def get_system_name(self) -> str:
        return 'libheif1'

    def get_dev_system_name(self) -> str:
        return 'libheif-dev'
    
dependency_index.Index().register_dependency(LibHeifDependency())