from libsw import dependency, dependency_index

class LibReadlineDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libreadline')

    def get_system_name(self) -> str:
        return 'libreadline8t64'

    def get_dev_system_name(self) -> str:
        return 'libreadline-dev'
    
dependency_index.Index().register_dependency(LibReadlineDependency())