from libsw import dependency, dependency_index

class LibOnigDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libonig')

    def get_system_name(self) -> str:
        return 'libonig5'

    def get_dev_system_name(self) -> str:
        return 'libonig-dev'
    
dependency_index.Index().register_dependency(LibOnigDependency())