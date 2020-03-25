#!/usr/bin/env python3

from libsw import build_index, nginx, openssl, modsec, curl, maxmind

index = build_index.Index()
index.register_builder( openssl.OpensslBuilder() )
index.register_builder( curl.CurlBuilder() )
index.register_builder( nginx.NginxCacheBuilder() )
index.register_builder( maxmind.MaxMindBuilder() )
index.register_builder( modsec.OwaspBuilder() )
index.register_builder( modsec.ModSecurityRulesetBuilder() )
index.register_builder( modsec.ModSecurityBuilder() )
index.register_builder( nginx.ModSecurityNginxBuilder() )
index.register_builder( nginx.NginxBuilder() )
