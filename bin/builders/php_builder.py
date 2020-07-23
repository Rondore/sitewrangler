#!/usr/bin/env python3

from libsw import build_index, curl, openssl, php, postgresql, image_magick, pecl_imagick, pecl_memcached, pecl_redis

index = build_index.Index()
index.register_builder( openssl.OpensslBuilder() )
index.register_builder( curl.CurlBuilder() )
index.register_builder( postgresql.PostgresqlBuilder() )
index.register_builder( php.ImapBuilder() )
index.register_builder( image_magick.ImageMagickBuilder() )
index.register_builder( pecl_imagick.ImagickBuilder() )
index.register_builder( pecl_memcached.MemcachedBuilder() )
index.register_builder( pecl_redis.RedisBuilder() )
for version in php.get_updated_versions():
    index.register_builder( php.PhpBuilder(version) )
