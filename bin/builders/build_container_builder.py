#!/usr/bin/env python3

from libsw import build_index, build_container

index = build_index.Index()
index.register_builder( build_container.BuildContainer() )