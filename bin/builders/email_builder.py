#!/usr/bin/env python3

from libsw import build_index, exim, dovecot

index = build_index.Index()
index.register_builder( exim.EximBuilder() )
index.register_builder( dovecot.DovecotBuilder() )