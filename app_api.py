#!/usr/bin/env python
# coding: utf-8

import ansible.utils.pybook as pybook
# :TRICKY: доступ к функционалу, идентичный для Pybooks
globals().update(pybook.book_globals)

def install_packages(name, lst):
    with mapping:
        append("name", name)
        with mapping("apt"):
            with sequence("pkg"):
                for item in lst:
                    append(item)


def install_ext_repo(apt_repository, key_id):
    with tasks:
        with mapping:
            with mapping("apt_key"):
                append("keyserver", "keyserver.ubuntu.com")
                append("id", key_id)

        with mapping:
            with mapping("apt_repository"):
                append("repo", apt_repository)
                append("state", "present")

def start_systemd_service(name):
    with mapping:
        append("name", "start systemd service: %(name)s" % locals())
        with mapping("systemd"):
            append("name",    name)
            append("state",   "started")
            append("enabled", "yes")

#
# Secrets are plain files in directory secrets like so:
#
# $ ls -1lR secrets/
# secrets/:
# total 8
# drwx------ 1 ilya ilya    0 мар 13 13:35 frankfurt-vpn-d0-starter-1
# drwx------ 1 ilya ilya 4096 апр  8 13:25 hm-bananapi-1
# drwx------ 1 ilya ilya 4096 сен 28  2019 paris-vpn-aws-t2-micro-1
# drwx------ 1 ilya ilya    0 мар 26 01:28 telegram_bot_AnkorauxUnuBot
#
# secrets/frankfurt-vpn-d0-starter-1:
# total 1
# -rwx------ 1 ilya ilya 45 мар 13 13:35 private.key
# -rwx------ 1 ilya ilya 45 мар 13 13:35 public.key
#
# secrets/hm-bananapi-1:
# total 2
# -rwx------ 1 ilya ilya 45 сен 25  2019 private.key
# -rwx------ 1 ilya ilya 45 сен 25  2019 public.key
# -rwx------ 1 ilya ilya 49 мар  8 20:38 wifi.yml
#
# secrets/paris-vpn-aws-t2-micro-1:
# total 2
# -rwx------ 1 ilya ilya  45 сен 25  2019 private.key
# -rwx------ 1 ilya ilya  45 сен 25  2019 public.key
#
# secrets/telegram_bot_AnkorauxUnuBot:
# total 1
# -rwx------ 1 ilya ilya 47 мар 26 01:28 telegram_bot.key
router_keys = "./secrets"

import os.path

def get_private_key(name):
    with open(os.path.join(router_keys, name)) as f:
        return f.read().strip("\n")

def get_wg_key(name, is_private):
    return get_private_key(os.path.join(name, "private.key" if is_private else "public.key"))

def install_dnsmasq():
    with tasks:
        install_packages("installing dnsmasq...", ["dnsmasq"])

        with mapping:
            append("name", "start dnsmasq")
            with mapping("systemd"):
                append("name",  "dnsmasq")
                append("state", "started")
                append("enabled", "yes")

        with mapping:
            append("name", "dnsmasq config")
            append("template", "src=router/dnsmasq-interfaces.conf.j2 dest=/etc/dnsmasq.d/interfaces.conf")

            with sequence("notify"):
                append("restart dnsmasq")

    with handlers:
        with mapping:
            append("name", "restart dnsmasq")
            append("systemd", "name=dnsmasq state=restarted")

