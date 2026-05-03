from libsw import dependency, dependency_index

class LibBz2Dependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libbz2')

    def get_system_name(self) -> str:
        return ' libbz2-1.0'

    def get_dev_system_name(self) -> str:
        return 'libbz2-dev'
    
dependency_index.Index().register_dependency(LibBz2Dependency())