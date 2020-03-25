#!/usr/bin/env python3

import os
from libsw import php, nginx, user

def make_php_site(user, domain, php_version):
    php.make_vhost(user, domain, php_version)
    nginx.make_vhost(user, domain)

if __name__ == '__main__':
    user = user.select_user()
    domain = input('New Domain: ')
    php_version = php.select_version()

    make_php_site(user, domain, php_version)
