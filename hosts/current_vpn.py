#!/usr/bin/env python3
# coding: utf-8

import yaml
import json

def get_current_vpn():
    yaml_kwargs = {}
    if "FullLoader" in dir(yaml):
        yaml_kwargs["Loader"] = yaml.FullLoader

    with open("group_vars/all") as f:
        dat = yaml.load(f, **yaml_kwargs)
        return dat["current_vpn"]

if __name__ == '__main__':
    current_vpn = get_current_vpn()

    inventory = {
        "_meta": {
            "hostvars" : {}
        },
        "current-vpn": {
            "hosts": [current_vpn],
        }
    }
    import sys
    json.dump(inventory, sys.stdout, indent=4, sort_keys=True)