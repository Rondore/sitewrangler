from libsw import dependency, dependency_index

class LibFontConfigDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libfontconfig')

    def get_system_name(self) -> str:
        return 'libfontconfig1'

    def get_dev_system_name(self) -> str:
        return 'libfontconfig1-dev'
    
dependency_index.Index().register_dependency(LibFontConfigDependency())