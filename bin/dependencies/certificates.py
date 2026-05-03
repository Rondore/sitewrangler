from libsw import dependency, dependency_index

class CertificatesDependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('certificates')

    def get_system_name(self) -> str:
        return 'ca-certificates'

    def get_dev_system_name(self) -> str:
        return 'ca-certificates'
    
dependency_index.Index().register_dependency(CertificatesDependency())