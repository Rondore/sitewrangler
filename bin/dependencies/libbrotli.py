from libsw import dependency, dependency_index

class LibBrotliDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libbrotli')

    def get_system_name(self) -> str:
        return 'libbrotli1'

    def get_dev_system_name(self) -> str:
        return 'libbrotli-dev'
    
dependency_index.Index().register_dependency(LibBrotliDependency())