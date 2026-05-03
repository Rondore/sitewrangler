from libsw import dependency, dependency_index

class BinutilsDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('binutils')

    def get_system_name(self) -> str:
        return 'binutils-common'

    def get_dev_system_name(self) -> str:
        return 'binutils-dev'
    
dependency_index.Index().register_dependency(BinutilsDependency())