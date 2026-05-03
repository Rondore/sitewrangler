from libsw import dependency, dependency_index

class LibXmlDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libxml')

    def get_system_name(self) -> str:
        return 'libxml2'

    def get_dev_system_name(self) -> str:
        return 'libxml2-dev'
    
dependency_index.Index().register_dependency(LibXmlDependency())