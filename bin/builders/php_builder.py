#!/usr/bin/env python3

from libsw import build_index, curl, openssl, php, postgresql

index = build_index.Index()
index.register_builder( openssl.OpensslBuilder() )
index.register_builder( curl.CurlBuilder() )
index.register_builder( postgresql.PostgresqlBuilder() )
index.register_builder( php.ImapBuilder() )
for version in php.get_updated_versions():
    index.register_builder( php.PhpBuilder(version) )
