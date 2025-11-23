"""Avi-on Mesh service for Home Assistant."""
import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from homeassistant.components import bluetooth as ha_bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

# Add the source module to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from avionhttp import http_list_devices
from avionmesh.Mesh import apply_overrides_from_settings
from avionmesh import mesh_handler

_LOGGER = logging.getLogger(__name__)

SIGNAL_MESH_STATUS_UPDATE = "avion_direct_mesh_status_update"


@dataclass
class MeshCommand:
    """Command to be sent to mesh."""

    data: dict


@dataclass
class MeshStatus:
    """Status update from mesh."""

    data: dict


class AvionMeshService:
    """Service that manages Avi-on mesh connection for Home Assistant."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the service."""
        self.hass = hass
        self.config_entry = config_entry
        self.command_queue: asyncio.Queue[MeshCommand] = asyncio.Queue()
        self.status_queue: asyncio.Queue[MeshStatus] = asyncio.Queue()
        self._mesh_handler_task: Optional[asyncio.Task] = None
        self._status_listener_task: Optional[asyncio.Task] = None
        self._location: Optional[dict] = None
        self._target_devices: List[str] = []
        self._passphrase: str = ""

    async def async_initialize(self) -> None:
        """Initialize the service and load configuration."""
        _LOGGER.info("Initializing Avi-on Mesh service")

        # Build settings from config entry data (moved from YAML into UI)
        settings = {}
        # Devices
        devices_cfg = {
            "import": bool(self.config_entry.data.get("import_devices", True)),
            "include": [
                s.strip()
                for s in self.config_entry.data.get("devices_include", "").split(",")
                if s.strip()
            ],
            "exclude": [
                s.strip()
                for s in self.config_entry.data.get("devices_exclude", "").split(",")
                if s.strip()
            ],
        }
        devices_cfg["exclude_in_group"] = bool(self.config_entry.data.get("exclude_in_group", True))
        settings["devices"] = devices_cfg

        # Groups
        groups_cfg = {
            "import": bool(self.config_entry.data.get("import_groups", True)),
            "include": [
                s.strip()
                for s in self.config_entry.data.get("groups_include", "").split(",")
                if s.strip()
            ],
            "exclude": [
                s.strip()
                for s in self.config_entry.data.get("groups_exclude", "").split(",")
                if s.strip()
            ],
        }
        settings["groups"] = groups_cfg

        # Single device and 'all' options
        if bool(self.config_entry.data.get("all_import", False)):
            settings.setdefault("all", {})["import"] = True
            settings["all"]["name"] = self.config_entry.data.get("all_name", "All Avi-on Devices")

        # Capability overrides
        cap_dimming = [
            int(s) for s in self.config_entry.data.get("cap_dimming", "").split(",") if s.strip()
        ]
        cap_color_temp = [
            int(s) for s in self.config_entry.data.get("cap_color_temp", "").split(",") if s.strip()
        ]
        if cap_dimming or cap_color_temp:
            settings.setdefault("capabilities_overrides", {})["dimming"] = cap_dimming
            settings.setdefault("capabilities_overrides", {})["color_temp"] = cap_color_temp

        # Apply mesh overrides from settings
        apply_overrides_from_settings(settings)

        # Get device information from Avi-on API
        email = self.config_entry.data.get("username", "")
        password = self.config_entry.data.get("password", "")

        _LOGGER.info(f"Fetching devices for {email}")
        locations = await http_list_devices(email, password)

        if not locations:
            raise ValueError("No locations found for this account")

        if len(locations) > 1:
            _LOGGER.warning(f"Multiple locations found ({len(locations)}), using first")

        self._location = locations[0]
        self._passphrase = self._location["passphrase"]
        self._target_devices = [d["mac_address"].upper() for d in self._location["devices"]]

        _LOGGER.info(f"Resolved {len(self._target_devices)} devices")

        # Get Home Assistant scanner and start mesh handler and status listener
        scanner = ha_bluetooth.async_get_scanner(self.hass)

        self._mesh_handler_task = asyncio.create_task(
            mesh_handler(
                self._passphrase,
                self._target_devices,
                self.command_queue,
                self.status_queue,
                scanner,
            )
        )
        self._status_listener_task = asyncio.create_task(self._listen_for_status_updates())

    async def _listen_for_status_updates(self) -> None:
        """Listen for status updates from mesh and dispatch them."""
        try:
            while True:
                status: MeshStatus = await self.status_queue.get()
                _LOGGER.debug(f"Status update from mesh: {status.data}")

                # Dispatch to listeners (light entities, etc.)
                async_dispatcher_send(self.hass, SIGNAL_MESH_STATUS_UPDATE, status.data)

                self.status_queue.task_done()
        except asyncio.CancelledError:
            _LOGGER.info("Status listener cancelled")
            raise

    async def send_mesh_command(self, command: dict) -> None:
        """Send a command to the mesh."""
        _LOGGER.debug(f"Sending mesh command: {command}")
        await self.command_queue.put(MeshCommand(data=command))

    def get_location(self) -> Optional[dict]:
        """Get the location data."""
        return self._location

    async def async_shutdown(self) -> None:
        """Shutdown the service."""
        _LOGGER.info("Shutting down Avi-on Mesh service")

        if self._mesh_handler_task and not self._mesh_handler_task.done():
            self._mesh_handler_task.cancel()
            try:
                await self._mesh_handler_task
            except asyncio.CancelledError:
                pass

        if self._status_listener_task and not self._status_listener_task.done():
            self._status_listener_task.cancel()
            try:
                await self._status_listener_task
            except asyncio.CancelledError:
                pass
