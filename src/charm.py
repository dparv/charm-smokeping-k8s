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

import templating
import json

logger = logging.getLogger(__name__)


class SmokepingCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.smokeping_pebble_ready, self._on_smokeping_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.restart_action, self._on_restart_action)

    def _on_smokeping_pebble_ready(self, event):
        self._configure_smokeping()

    def _configure_smokeping(self):
        self.unit.status = MaintenanceStatus('Configuring Smokeping')

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
                        "PUID": "1000",
                        "PGID": "1000"
                    },
                }
            },
        }

        self._render_config()

        container = self.unit.get_container("smokeping")
        container.add_layer("smokeping", pebble_layer, combine=True)

        if container.get_service("smokeping").is_running():
            container.stop("smokeping")
        container.start("smokeping")

        self.unit.status = ActiveStatus()


    def _on_config_changed(self, _):
        self.unit.status = MaintenanceStatus('Updating configuration')

        self._configure_smokeping()

        self.unit.status = ActiveStatus()

    def _render_config(self):
        container = self.unit.get_container('smokeping')
        context = {
            'config': self.config,
            'destinations': self._destinations,
        }
        container.push("/config/Targets", templating.render(self.charm_dir, "Targets", context))
        container.push("/config/Database", templating.render(self.charm_dir, "Database", context))

        try:
            service = container.get_service("smokeping")
        except ModelError:
            # NOTE: Most likely the PebbleReadyEvent didn't fire yet, so there's no service to restart.
            return

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
            if container.get_service("smokeping").is_running():
                container.stop("smokeping")
            container.start("smokeping")
        except ModelError as e:
            event.fail(message=str(e))


if __name__ == "__main__":
    main(SmokepingCharm)
