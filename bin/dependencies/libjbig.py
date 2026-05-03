from libsw import dependency, dependency_index

class LibJbigDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libjbig')

    def get_system_name(self) -> str:
        return 'libjbig0'

    def get_dev_system_name(self) -> str:
        return 'libjbig-dev'
    
dependency_index.Index().register_dependency(LibJbigDependency())