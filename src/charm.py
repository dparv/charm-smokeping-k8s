#!/usr/bin/env python3
# Copyright 2021 Diko Parvanov

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, ModelError
from ops.pebble import ChangeError

import templating
import json

logger = logging.getLogger(__name__)

CONTAINER = "smokeping"
SMOKEPING_SERVICE = "smokeping"
APACHE_SERVICE = "apache"

class SmokepingCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.smokeping_pebble_ready, self._on_smokeping_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.restart_action, self._on_restart_action)

    def _on_smokeping_pebble_ready(self, event):
        self._render_config_and_run()

    def _on_config_changed(self, _):
        self._render_config_and_run()

    def _render_config_and_run(self):
        self.unit.status = MaintenanceStatus('Configuring Smokeping')

        container = self.unit.get_container(CONTAINER)

        pebble_smokeping_layer = {
            "summary": "smokeping layer",
            "description": "pebble config layer for smokeping ",
            "services": {
                "smokeping": {
                    "override": "replace",
                    "summary": "smokeping",
                    "command": "/usr/bin/perl /usr/bin/smokeping --config=/etc/smokeping/config --nodaemon",
                    "startup": "enabled",
                    "environment": {
                        "TZ": self.config['timezone'],
                    },
                },
                "apache": {
                    "override": "replace",
                    "summary": "apache",
                    "command": "/start_apache.sh",
                    "startup": "enabled",
                }
            }
        }

        container.add_layer(SMOKEPING_SERVICE, pebble_smokeping_layer, combine=True)

        context = {
            'config': self.config,
            'destinations': self._destinations,
        }
        container.make_dir("/var/cache/smokeping", user="abc", group="abc", make_parents=True)
        container.push("/config/General", templating.render(self.charm_dir, "General"))
        container.push("/config/Alerts", templating.render(self.charm_dir, "Alerts"))
        container.push("/config/Presentation", templating.render(self.charm_dir, "Presentation"))
        container.push("/config/Probes", templating.render(self.charm_dir, "Probes"))
        container.push("/config/Slaves", templating.render(self.charm_dir,"Slaves"))
        container.push("/config/Targets", templating.render(self.charm_dir, "Targets", context))
        container.push("/config/Database", templating.render(self.charm_dir, "Database", context))
        container.push("/config/pathnames", templating.render(self.charm_dir, "pathnames"))
        container.push("/etc/apache2/httpd.conf", templating.render(self.charm_dir, "httpd.conf"))
        container.push("/start_apache.sh", templating.render(self.charm_dir, "start_apache.sh"), permissions=0o755)

        self._restart_container_service(CONTAINER, SMOKEPING_SERVICE)
        self._restart_container_service(CONTAINER, APACHE_SERVICE)

        self.unit.status = ActiveStatus()

    @property
    def _destinations(self):
        targets = []
        try:
            targets = json.loads(self.config['targets'])
        except json.decoder.JSONDecodeError:
            # malformed JSON code, throw error and go into blocked state
            self.unit.status = BlockedStatus('Malformed JSON config for targets.')

        return targets

    def _on_restart_action(self, event):
        event.log("Restarting Smokeping services")
        try:
            self._restart_container_service(CONTAINER, SMOKEPING_SERVICE)
            self._restart_container_service(CONTAINER, APACHE_SERVICE)
        except ModelError as e:
            event.fail(message=str(e))

    def _restart_container_service(self, container_name, svc_name):
        container = self.unit.get_container(container_name)
        if not container:
            msg = "Container {} not found".format(container_name)
            logger.error(msg)
            return

        service = container.get_service(svc_name)
        if service and service.is_running():
            container.stop(svc_name)
        container.start(svc_name)


if __name__ == "__main__":
    main(SmokepingCharm)
