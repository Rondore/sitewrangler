from libsw import dependency, dependency_index

class LibJpegDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('libjpeg')

    def get_system_name(self) -> str:
        return ' libjpeg62-turbo'

    def get_dev_system_name(self) -> str:
        return 'libjpeg-dev'
    
dependency_index.Index().register_dependency(LibJpegDependency())