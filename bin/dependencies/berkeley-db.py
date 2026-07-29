from libsw import dependency, dependency_index

class BerkeleyDbDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('berkeley-db')

    def get_system_name(self) -> str:
        return 'libdb-dev'

    def get_dev_system_name(self) -> str:
        return 'libdb-dev'
    
dependency_index.Index().register_dependency(BerkeleyDbDependency())