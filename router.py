#!/usr/bin/env python3
# coding: utf-8

import app_api
install_packages = app_api.install_packages
router_keys = app_api.router_keys
get_key = app_api.get_wg_key

import os.path

def wg_quick(wg_conf_num, template, name, peer_name, **additional_vars):
    wg_quick_name = "wg-quick@wg%(wg_conf_num)s" % locals()
    handler_name  = "restart %(wg_quick_name)s" % locals()

    with tasks:
        with mapping:
            append("name", "wg config: %(wg_conf_num)s" % locals())
            append("template", "src=%(template)s dest=/etc/wireguard/wg%(wg_conf_num)s.conf" % locals())
            with mapping("vars"):
                append("private_key", get_key(name, True))
                append("peer_public_key",     get_key(peer_name, False))

                for k, v in additional_vars.items():
                    append(k, v)

            with sequence("notify"):
                append(handler_name)

        with mapping:
            append("name", "start %(wg_quick_name)s service" % locals())
            with mapping("systemd"):
                append("name",  wg_quick_name)
                append("state", "started")
                append("enabled", "yes")

    with handlers:
        with mapping:
            append("name", handler_name)
            append("systemd", "name=%(wg_quick_name)s state=restarted" % locals())


import current_vpn
current_vpn_name = current_vpn.get_current_vpn()


install_ext_repo = app_api.install_ext_repo

def install_bird(conf_template):
    with tasks:
        install_packages("installing bird...", ["bird"])

        with mapping:
            append("name", "start bird")
            with mapping("systemd"):
                append("name",  "bird")
                append("state", "started")
                append("enabled", "yes")

        with mapping:
            append("name", "stop bird6")
            with mapping("systemd"):
                append("name",  "bird6")
                append("state", "stopped")
                append("enabled", "no")

        with mapping:
            append("name", "bird config")
            append("template", "src=%(conf_template)s dest=/etc/bird/bird.conf" % locals())

            with sequence("notify"):
                append("reconfigure bird")

    with handlers:
        with mapping:
            append("name", "reconfigure bird")
            append("command", "birdc configure")

def enable_ip_forward():
    # sudo sysctl net.ipv4.ip_forward
    # => 1
    with tasks:
        with mapping:
            with mapping("sysctl"):
                append("name",  "net.ipv4.ip_forward")
                append("value", "1")

prom_collect_path = "/var/lib/prometheus/node-exporter"

with mapping:
    append("hosts", "current-vpn")

    # wireguard
    install_ext_repo("deb http://ppa.launchpad.net/wireguard/wireguard/ubuntu bionic main",
                          "E1B39B6EF6DDB96564797591AE33835F504A1A25")
    with tasks:
        install_packages("installing wireguard...", ["wireguard"])

    wg_conf_num = 0
    template = "vpn/wg-vpn-router.conf.j2"
    wg_quick(wg_conf_num, template, current_vpn_name, "hm-bananapi-1")

    # bird
    install_ext_repo("deb http://ppa.launchpad.net/cz.nic-labs/bird/ubuntu bionic main",
                          "52463488670E69A092007C24F2331238F9C59A45")
    install_bird("vpn/bird.conf.j2")

    # update_rkn_blacklist.sh
    with tasks:
        install_packages("installing moreutils...", ["moreutils"])

        with mapping:
            append("name", "update_rkn_blacklist.sh")
            with mapping("template"):
                append("src",  "vpn/update_rkn_blacklist.sh.j2")
                append("dest", "/usr/local/sbin/update_rkn_blacklist.sh")
                append("mode", "755")

            with sequence("notify"):
                append("run update_rkn_blacklist.sh")

        # https://crontab.guru/every-30-minutes
        # crontab -l => */30 * * * *
        with mapping:
            append("name", "ensure update_rkn_blacklist.sh that runs every 30 min")
            with mapping("cron"):
                append("name", "update_rkn_blacklist.sh")
                append("minute", "*/30")
                append("job",  "/usr/local/sbin/update_rkn_blacklist.sh")

    with handlers:
        with mapping:
            append("name", "run update_rkn_blacklist.sh")
            append("command", "/usr/local/sbin/update_rkn_blacklist.sh")

    enable_ip_forward()

    # monitoring
    with tasks:
        # bird_exporter
        with mapping:
            append("name", "download bird_exporter binary")
            with mapping("get_url"):
                append("url", "https://github.com/czerwonk/bird_exporter/releases/download/1.2.4/bird_exporter-1.2.4_linux_amd64")
                append("dest", "/usr/local/sbin/bird_exporter")
                append("checksum", "sha1:86b6ca88197d71708e4cf8168b2b17fe64e84ef0")
                append("mode", "755")

        with mapping:
            append("template", "src=vpn/bird_exporter.service.j2 dest=/lib/systemd/system/bird_exporter.service mode=644")
            with mapping("vars"):
                append("listen_address", "172.30.0.9")

            with sequence("notify"):
                append("reload systemctl")

        app_api.start_systemd_service("bird_exporter")

        # node_exporter
        with mapping:
            append("name", "download node_exporter binary")
            with mapping("get_url"):
                append("url", "https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz")
                append("dest", "/tmp")
                append("checksum", "sha256:b2503fd932f85f4e5baf161268854bf5d22001869b84f00fd2d1f57b51b72424")

        # tar -xzvpf /tmp/node_exporter-0.18.1.linux-amd64.tar.gz -C /tmp --strip-components 1  --add-file node_exporter-0.18.1.linux-amd64/node_exporter
        with mapping:
            with mapping("unarchive"):
                append("src", "/tmp/node_exporter-0.18.1.linux-amd64.tar.gz")
                append("dest", "/usr/local/bin")
                append("remote_src", "yes")
                append("extra_opts", "--strip-components 1 --add-file node_exporter-0.18.1.linux-amd64/node_exporter".split())

        # installing like the Debian packagers does it
        with mapping:
            append("name",  "create Prometheus group")
            append("group", "name=prometheus state=present")

        with mapping:
            append("name",  "create Prometheus user")
            append("user",  "name=prometheus group=prometheus createhome=no shell=/sbin/nologin comment='Prometheus daemon' state=present")

        with mapping:
            prom_collect_path
            append("file", "path=%(prom_collect_path)s state=directory owner=prometheus group=prometheus" % locals())

        # :REFACTOR:
        with mapping:
            append("template", "src=vpn/node_exporter.service.j2 dest=/lib/systemd/system/node_exporter.service mode=644")
            with mapping("vars"):
                append("prom_collect_path", prom_collect_path)
                append("listen_address",    "172.30.0.9")

            with sequence("notify"):
                append("reload systemctl")

        app_api.start_systemd_service("node_exporter")

    with handlers:
        with mapping:
            append("name", "reload systemctl")
            append("command", "systemctl daemon-reload")

def notify_about_manual_action(msg, when):
    with mapping:
        with mapping("debug"):
            append("msg", msg)
        append("when",  when)

with mapping:
    append("hosts", "routers")

    with tasks:
        with mapping:
            append("name", "/etc/network/interfaces")
            append("template", "src=router/interfaces.j2 dest=/etc/network/interfaces")
            append("register", "interfaces")

        notify_about_manual_action("You need to 'systemctl restart networking'", "interfaces.changed")

        # router0
        with when("router0 is defined"):
            with mapping:
                append("name", "rename lan0 => router0")
                append("template", "src=router/lan0-router0.link.j2 dest=/etc/systemd/network/50-lan0-router0.link")
                append("register", "rename_lan0_router0")

        with when("not(router0 is defined)"):
            with mapping:
                append("file", "state=absent path=/etc/systemd/network/50-lan0-router0.link")
                append("register", "rename_lan0_router0")

        notify_about_manual_action("You need to restart the system to get renamed network interface lan0 to router0", "rename_lan0_router0.changed")

        # dhclient
        with mapping:
            with mapping("blockinfile"):
                append("dest", "/etc/dhcp/dhclient.conf")
                append("block",
"""# udhcpc defaults
timeout 9;
retry 20;
""")
            append("register", "dhclient_timeouts")

        notify_about_manual_action("You need to 'systemctl restart networking' to apply shortened timeouts at dhclient",
                                   "dhclient_timeouts.changed")

    # wireguard
    wg_conf_num = 1
    template = "router/wg-router-vpn.conf.j2"
    wg_quick(wg_conf_num, template, "hm-bananapi-1", current_vpn_name, **{
        # :KLUDGE: do it in the very wg1.conf
        "peer_public_ip": current_vpn.load_yaml("host_vars/%(current_vpn_name)s.yml" % locals())["public-ip"],
    })

    # bird
    install_bird("router/bird.conf.j2")

    # dnsmasq
    app_api.install_dnsmasq()

    # sudo sysctl net.ipv4.ip_forward
    # => 1
    enable_ip_forward()

    # nftables
    with tasks:
        install_packages("installing nftables...", ["nftables"])

        with mapping:
            append("name", "start nftables")
            with mapping("systemd"):
                append("name",  "nftables")
                append("state", "started")
                append("enabled", "yes")

        with mapping:
            append("name", "nftables config")
            append("template", "src=router/nftables.conf.j2 dest=/etc/nftables.conf")

            with sequence("notify"):
                append("restart nftables")

    with handlers:
        with mapping:
            append("name", "restart nftables")
            append("systemd", "name=nftables state=restarted")

    # wifi
    with tasks:
        with mapping:
            append("name", "mt7622 before rfkill hack")
            append("template", "src=router/modprobe-wifi.conf.j2 dest=/etc/modprobe.d/wifi.conf")
            append("register", "mt7622_hack")

        notify_about_manual_action("You need to restart the system to make use of Wi-fi if dmesg | grep -Ei 'mt7622.*(fail|err)'",
                                   "mt7622_hack.changed")

        host_apd_conf = "/etc/hostapd/hostapd.conf"

        with mapping:
            with mapping("lineinfile"):
                append("dest", "/etc/default/hostapd")
                append("regexp", "^#?DAEMON_CONF.*=")
                append("line", """DAEMON_CONF=%(host_apd_conf)s""" % locals())

            with sequence("notify"):
                append("restart hostapd")

        import yaml
        with open(os.path.join(router_keys, "hm-bananapi-1/wifi.yml")) as f:
            wifi = yaml.load(f, yaml.FullLoader)

        with mapping:
            append("name", "hostapd config")
            append("template", "src=router/hostapd.conf.j2 dest=%(host_apd_conf)s" % locals())
            with mapping("vars"):
                append("ssid",           wifi["ssid"])
                append("wpa_passphrase", wifi["wpa_passphrase"])

            with sequence("notify"):
                append("restart hostapd")

        with mapping:
            append("name", "start hostapd")
            with mapping("systemd"):
                append("name",  "hostapd")
                append("state", "started")
                append("enabled", "yes")


    with handlers:
        with mapping:
            append("name", "restart hostapd")
            append("systemd", "name=hostapd state=restarted")

    with tasks:
        install_packages("installing node_exporter...", ["prometheus-node-exporter"])

        with mapping:
            append("name", "vpn_latency_metrics.sh")
            with mapping("template"):
                append("src",  "monitoring/vpn_latency_metrics.sh")
                append("dest", "/usr/local/bin/vpn_latency_metrics.sh")
                append("mode", "755")

        prom_collect_path
        with mapping:
            append("name", "ensure vpn_latency_metrics.sh that runs every minute")
            with mapping("cron"):
                append("name", "vpn_latency_metrics.sh")
                append("minute", "*")
                append("job",  '''/bin/bash -c "/usr/local/bin/vpn_latency_metrics.sh | env TMPDIR=%(prom_collect_path)s sponge %(prom_collect_path)s/vpn_latency_metrics.prom"''' % locals())
