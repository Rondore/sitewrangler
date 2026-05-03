from libsw import dependency, dependency_index

class LibGompDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libgomp')

    def get_system_name(self) -> str:
        return 'libgomp1'

    def get_dev_system_name(self) -> str:
        return 'libgomp1'
    
dependency_index.Index().register_dependency(LibGompDependency())