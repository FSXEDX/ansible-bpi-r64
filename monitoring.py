#!/usr/bin/env python3
# coding: utf-8

import app_api
install_packages = app_api.install_packages

def own_by_root():
    append("owner", "root")
    append("group", "root")
    append("mode", "0644")

with mapping:
    append("hosts", "monitoring")

    # docker

    # `lsb_release -cs`
    release = "bionic"
    # $ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg -- 2> /dev/null | grep '^ '
    #       9DC858229FC7DD38854AE2D88D81803C0EBFCD88
    app_api.install_ext_repo("deb [arch=amd64] https://download.docker.com/linux/ubuntu %(release)s stable" % locals(),
                             "9DC858229FC7DD38854AE2D88D81803C0EBFCD88")

    with tasks:
        install_packages("installing docker", ["docker-ce"])
        app_api.start_systemd_service("docker")
        install_packages("python3-docker", ["python3-docker"])

        # prometheus
        for path in ["/prometheus", "/etc/prometheus", "/etc/prometheus/auto_http"]:
            with mapping:
                # 65534 = nobody in base de prometheus image
                append("file", "path=%(path)s state=directory owner=65534" % locals())

        with mapping:
            with mapping("template"):
                append("src",  "monitoring/prometheus.yml.j2")
                append("dest", "/etc/prometheus/prometheus.yml")

                own_by_root()

            with sequence("notify"):
                append("reload prometheus")

        with mapping:
            append("name", "sync prom rules")
            with mapping("synchronize"):
                append("src", "monitoring/rules/")
                append("dest", "/etc/prometheus/rules")
                append("delete", "yes")

                append("owner", "false")
                append("group", "false")
                append("perms", "false")

            with sequence("notify"):
                append("reload prometheus")

        with mapping:
            append("name", "prometheus in docker")
            with mapping("include_role"):
                append("name", "mhutter.docker-systemd-service")
            with mapping("vars"):
                append("container_name",  "prometheus")
                append("container_image", "prom/prometheus:v2.16.0")
                append("container_cmd",   "--config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=30d --web.listen-address=0.0.0.0:9090 --log.level=info --web.console.libraries=/usr/share/prometheus/console_libraries --web.console.templates=/usr/share/prometheus/consoles")
                append("container_volumes", ["/prometheus:/prometheus", "/etc/prometheus:/etc/prometheus"])
                append("container_host_network", True)

        # alertmanager
        for path in ["/alertmanager", "/etc/alertmanager", "/etc/alertmanager/template"]:
            with mapping:
                # 65534 = nobody in base de prometheus image
                append("file", "path=%(path)s state=directory owner=65534" % locals())

        with mapping:
            with mapping("template"):
                append("src",  "monitoring/alertmanager.yml.j2")
                append("dest", "/etc/alertmanager/alertmanager.yml")

                own_by_root()
            with sequence("notify"):
                append("reload alertmanager")

        with mapping:
            append("name", "alertmanager in docker")
            with mapping("include_role"):
                append("name", "mhutter.docker-systemd-service")
            with mapping("vars"):
                append("container_name",  "alertmanager")
                append("container_image", "quay.io/prometheus/alertmanager:v0.20.0")
                log_level = "debug" # "info" #
                append("container_cmd",   "--config.file=/etc/alertmanager/alertmanager.yml --web.listen-address=0.0.0.0:9093 --storage.path=/alertmanager --log.level=%(log_level)s" % locals())
                append("container_volumes", ["/alertmanager:/alertmanager", "/etc/alertmanager:/etc/alertmanager"])
                append("container_host_network", True)

        # tor
        install_packages("tor", ["tor"])
        with mapping:
            append("file", "path=/etc/tor state=directory")

        with mapping:
            with mapping("template"):
                append("src",  "monitoring/torrc.j2")
                append("dest", "/etc/tor/torrc")

                own_by_root()
            with sequence("notify"):
                append("reload tor")

        # :TODO: https://tor.stackexchange.com/a/15191 - about AppArmor vs Directory /var/lib/tor cannot be read: Permission denied
        app_api.start_systemd_service("tor@default")

        # alertmanager-bot: webhook to Telegram
        for path in ["/etc/alertmanager-bot", "/alertmanager-bot"]:
            with mapping:
                append("file", "path=%(path)s state=directory" % locals())

        with mapping:
            with mapping("template"):
                append("src",  "monitoring/alertmanager-bot.template.j2")
                append("dest", "/etc/alertmanager-bot/default.tmpl")

                own_by_root()
            with sequence("notify"):
                append("restart alertmanager-bot")

        telegram_key = app_api.get_private_key("telegram_bot_AnkorauxUnuBot/telegram_bot.key")

        with mapping:
            append("name", "alertmanager-bot in docker")
            with mapping("include_role"):
                append("name", "mhutter.docker-systemd-service")
            with mapping("vars"):
                append("container_name",  "alertmanager-bot")
                append("container_image", "metalmatze/alertmanager-bot:0.4.2")
                append("container_cmd",   "--telegram.admin={{ telegram_bot_admins | join(' --telegram.admin=') }} --store=bolt --bolt.path=/alertmanager-bot/bot.db --listen.addr=localhost:9095 --template.paths=/etc/alertmanager-bot/default.tmpl")
                append("container_volumes", ["/etc/alertmanager-bot/default.tmpl:/etc/alertmanager-bot/default.tmpl", "/alertmanager-bot:/alertmanager-bot"])
                append("container_host_network", True)
                with mapping("container_env"):
                    append("TELEGRAM_TOKEN", telegram_key)
                    append("HTTP_PROXY", "socks5://127.0.0.1:9050")

        # blackbox_exporter
        for path in ["/etc/blackbox_exporter"]:
            with mapping:
                append("file", "path=%(path)s state=directory" % locals())

        with mapping:
            with mapping("template"):
                append("src",  "monitoring/blackbox_exporter.yml.j2")
                append("dest", "/etc/blackbox_exporter/config.yml")

                own_by_root()
            with sequence("notify"):
                append("reload blackbox_exporter")

        with mapping:
            append("name", "blackbox_exporter in docker")
            with mapping("include_role"):
                append("name", "mhutter.docker-systemd-service")
            with mapping("vars"):
                append("container_name",  "blackbox_exporter")
                append("container_image", "prom/blackbox-exporter:v0.16.0")
                append("container_cmd",   "--config.file=/etc/blackbox_exporter/config.yml")
                append("container_volumes", ["/etc/blackbox_exporter/config.yml:/etc/blackbox_exporter/config.yml"])
                append("container_host_network", True)

    with handlers:
        with mapping:
            append("name", "reload prometheus")
            append("command", "docker kill --signal=SIGHUP prometheus")

        with mapping:
            append("name", "reload alertmanager")
            append("command", "docker kill --signal=SIGHUP alertmanager")

        with mapping:
            append("name", "reload tor")
            append("command", "systemctl reload tor.service")

        with mapping:
            append("name", "restart alertmanager-bot")
            append("command", "systemctl restart alertmanager-bot_container.service")

        with mapping:
            append("name", "reload blackbox_exporter")
            append("command", "docker kill --signal=SIGHUP blackbox_exporter")
