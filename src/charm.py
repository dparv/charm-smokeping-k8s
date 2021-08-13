#!/usr/bin/env python3
# Copyright 2021 Diko Parvanov
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, ModelError
from ops.pebble import ChangeError

import templating
import json

logger = logging.getLogger(__name__)

SERVICE = "smokeping"

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

        container = self.unit.get_container(SERVICE)

        pebble_layer = {
            "summary": "smokeping layer",
            "description": "pebble config layer for smokeping ",
            "services": {
                "smokeping": {
                    "override": "replace",
                    "summary": "smokeping",
                    "command": "/init",
                    "startup": "enabled",
                    "environment": {
                        "TZ": self.config['timezone'],
                    },
                }
            },
        }

        container.add_layer(SERVICE, pebble_layer, combine=True)

        context = {
            'config': self.config,
            'destinations': self._destinations,
        }
        container.push("/config/Targets", templating.render(self.charm_dir, "Targets", context))
        container.push("/config/Database", templating.render(self.charm_dir, "Database", context))

        if container.get_service(SERVICE).is_running():
            container.stop(SERVICE)
        container.start(SERVICE)

        self.unit.status = ActiveStatus()

    @property
    def _destinations(self):
        targets = []
        try:
            targets = json.loads(self.config['targets'])
        except JSONDecodeError:
            # malformed JSON code, throw error and go into blocked state
            self.unit.status = BlockedStatus('Malformed JSON config for targets.')

        return targets

    def _on_restart_action(self, event):
        event.log("Restarting Smokeping services")
        try:
            self._restart_container_service(SERVICE, SERVICE)
        except ModelError as e:
            event.fail(message=str(e))

    def _restart_container_service(self, container_name, svc_name):
        container = self.unit.get_container(container_name)
        if not container:
            msg = "Container {} not found".format(container_name)
            logger.error(msg)
            return

        if container.get_service(svc_name).is_running():
            container.stop(svc_name)
        container.start(svc_name)


if __name__ == "__main__":
    main(SmokepingCharm)
