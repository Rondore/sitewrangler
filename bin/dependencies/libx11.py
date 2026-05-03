from libsw import dependency, dependency_index

class LibX11Dependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libx11')

    def get_system_name(self) -> str:
        return 'libx11-6'

    def get_dev_system_name(self) -> str:
        return 'libx11-dev'
    
dependency_index.Index().register_dependency(LibX11Dependency())