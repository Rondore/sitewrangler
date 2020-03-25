#!/usr/bin/env python3

from libsw import build_index, curl, openssl, php, postgresql

version_list = php.get_versions()
index = build_index.Index()
if len(version_list) > 0:
    index.register_builder( openssl.OpensslBuilder() )
    index.register_builder( curl.CurlBuilder() )
    index.register_builder( postgresql.PostgresqlBuilder() )
    index.register_builder( php.ImapBuilder() )
    for version in php.get_versions():
        index.register_builder( php.PhpBuilder(version) )
