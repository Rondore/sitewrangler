from libsw import dependency, dependency_index

class LibXsltDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libxslt')

    def get_system_name(self) -> str:
        return 'libxslt1.1'

    def get_dev_system_name(self) -> str:
        return 'libxslt1-dev'
    
dependency_index.Index().register_dependency(LibXsltDependency())