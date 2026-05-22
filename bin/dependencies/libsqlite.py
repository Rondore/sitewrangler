from libsw import dependency, dependency_index

class LibSqliteDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libsqlite')

    def get_system_name(self) -> str:
        return 'libsqlite3-0'

    def get_dev_system_name(self) -> str:
        return 'libsqlite3-dev'
    
dependency_index.Index().register_dependency(LibSqliteDependency())