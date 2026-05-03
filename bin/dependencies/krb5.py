from libsw import dependency, dependency_index

class Krb5Dependency(dependency.Dependency):
    """
    A class to interact with a system package.
    """
    def __init__(self):
        super().__init__('krb5')

    def get_system_name(self) -> str:
        return 'libgssapi-krb5-2'

    def get_dev_system_name(self) -> str:
        return 'libkrb5-dev'
    
dependency_index.Index().register_dependency(Krb5Dependency())