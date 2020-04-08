#!/usr/bin/env python3
# coding: utf-8

import yaml

def load_yaml(path):
    yaml_kwargs = {}
    if "FullLoader" in dir(yaml):
        yaml_kwargs["Loader"] = yaml.FullLoader

    with open(path) as f:
        return yaml.load(f, **yaml_kwargs)

def get_current_vpn():
    dat = load_yaml("group_vars/all")
    return dat["current_vpn"]

