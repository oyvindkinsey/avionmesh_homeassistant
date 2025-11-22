"""Light platform for Avi-on Direct integration."""
import json
import logging
from typing import Any, List, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from avionmqtt.Mesh import CAPABILITIES, PRODUCT_NAMES

from . import DOMAIN
from .ha_service import SIGNAL_MESH_STATUS_UPDATE, AvionDirectService

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light entities for Avi-on Direct."""
    service: AvionDirectService = hass.data[DOMAIN][config_entry.entry_id]
    location = service.get_location()

    if not location:
        _LOGGER.error("Location data not available")
        return

    devices_cfg = {
        "import": bool(config_entry.data.get("import_devices", True)),
        "include": [
            s.strip() for s in config_entry.data.get("devices_include", "").split(",") if s.strip()
        ],
        "exclude": [
            s.strip() for s in config_entry.data.get("devices_exclude", "").split(",") if s.strip()
        ],
    }
    devices_cfg["exclude_in_group"] = bool(config_entry.data.get("exclude_in_group", True))

    groups_cfg = {
        "import": bool(config_entry.data.get("import_groups", True)),
        "include": [
            s.strip() for s in config_entry.data.get("groups_include", "").split(",") if s.strip()
        ],
        "exclude": [
            s.strip() for s in config_entry.data.get("groups_exclude", "").split(",") if s.strip()
        ],
    }

    all_cfg = {}
    if bool(config_entry.data.get("all_import", False)):
        all_cfg["name"] = config_entry.data.get("all_name", "All Avi-on Devices")

    dimming_overrides = [
        s.strip() for s in config_entry.data.get("cap_dimming", "").split(",") if s.strip()
    ]
    for product_id in dimming_overrides:
        CAPABILITIES["dimming"].add(product_id)
    color_temp_overrides = [
        s.strip() for s in config_entry.data.get("cap_color_temp", "").split(",") if s.strip()
    ]
    for product_id in color_temp_overrides:
        CAPABILITIES["color_temp"].add(product_id)

    entities: List[LightEntity] = []

    def _should_include(entity: dict, cfg: dict) -> bool:
        include = cfg.get("include")
        exclude = cfg.get("exclude")
        pid = entity.get("pid")
        if include:
            return pid in include
        return pid not in exclude

    # Handle groups
    if groups_cfg.get("import"):
        for group in location.get("groups", []):
            if _should_include(group, groups_cfg):
                entities.append(AvionDirectLight(service, group))

    # Handle devices (respect exclude_in_group behavior)
    if devices_cfg.get("exclude_in_group"):
        exclude = set(devices_cfg.get("exclude", []))
        for group in location.get("groups", []):
            for d in group.get("devices", []):
                exclude.add(d)
        devices_cfg["exclude"] = list(exclude)

    if devices_cfg.get("import"):
        for device in location.get("devices", []):
            if _should_include(device, devices_cfg):
                entities.append(AvionDirectLight(service, device))

    # Optional 'all' entity
    if all_cfg:
        all_name = all_cfg.get("name", "All Avi-on Devices")
        entities.append(
            AvionDirectLight(
                service, {"pid": "avion_all", "product_id": 0, "avid": 0, "name": all_name}
            )
        )

    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} light entities")


class AvionDirectLight(LightEntity):
    """Representation of an Avi-on light."""

    def __init__(self, service: AvionDirectService, device: dict):
        """Initialize the light."""
        self.service = service
        self._device = device
        self._attr_unique_id = device.get("pid", device.get("avid"))
        self._attr_name = device.get("name", f"Unknown ({device.get('avid')})")

        product_id = device.get("product_id", 0)
        self._product_id = product_id
        self._avid = device.get("avid")

        # Determine supported color modes and features
        supported_modes: set[ColorMode] = set()

        if product_id in CAPABILITIES["color_temp"]:
            supported_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = 2700
            self._attr_max_color_temp_kelvin = 5000
        elif product_id in CAPABILITIES["dimming"]:
            supported_modes.add(ColorMode.BRIGHTNESS)

        # If no special modes, expose plain on/off
        if not supported_modes:
            supported_modes = {ColorMode.ONOFF}

        self._attr_supported_color_modes = supported_modes

        # Set a sensible default color mode

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.get("pid", device.get("avid")))},
            "name": self._attr_name,
            "manufacturer": "Avi-on",
            "model": PRODUCT_NAMES.get(product_id, f"Unknown ({product_id})"),
            "serial_number": device.get("pid"),
        }

        # State (color_temp stored in kelvin)
        self._brightness: int = 0
        self._color_temp_kelvin: Optional[int] = None
        self._is_on: bool = False

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_MESH_STATUS_UPDATE,
                self._handle_mesh_update,
            )
        )

    @callback
    def _handle_mesh_update(self, status: dict) -> None:
        """Handle status update from mesh."""
        avid = status.get("avid")

        if avid != self._avid:
            return

        _LOGGER.debug(f"Received status for {self._attr_name}: {status}")

        if "brightness" in status:
            brightness = status["brightness"]
            self._brightness = brightness
            self._is_on = brightness > 0
            if brightness > 0:
                self._attr_color_mode = (
                    ColorMode.BRIGHTNESS
                    if self._product_id in CAPABILITIES["dimming"]
                    else ColorMode.ONOFF
                )
            else:
                self._attr_color_mode = ColorMode.ONOFF

        elif "color_temp" in status:
            self._color_temp_kelvin = status["color_temp"]
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._is_on = True

        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self._is_on

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of the light."""
        return self._brightness if self._product_id in CAPABILITIES["dimming"] else None

    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """Return the color temperature in kelvin."""
        return self._color_temp_kelvin if self._product_id in CAPABILITIES["color_temp"] else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        _LOGGER.debug(f"Turning on {self._attr_name} with kwargs: {kwargs}")

        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        payload = {}

        if color_temp_kelvin is not None and self._product_id in CAPABILITIES["color_temp"]:
            payload["color_temp"] = color_temp_kelvin
        elif brightness is not None and self._product_id in CAPABILITIES["dimming"]:
            payload["brightness"] = brightness
        else:
            payload["state"] = STATE_ON

        command = {
            "avid": self._avid,
            "command": "update",
            "json": json.dumps(payload),
        }

        await self.service.send_mesh_command(command)

        # Update local state
        if color_temp_kelvin is not None:
            self._color_temp_kelvin = color_temp_kelvin
            self._is_on = True
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif brightness is not None:
            self._brightness = brightness
            self._is_on = True
            self._attr_color_mode = ColorMode.BRIGHTNESS if brightness > 0 else ColorMode.ONOFF
        else:
            self._is_on = True

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self._attr_name}")

        payload = {"state": STATE_OFF}
        command = {
            "avid": self._avid,
            "command": "update",
            "json": json.dumps(payload),
        }

        await self.service.send_mesh_command(command)

        # Update local state
        self._is_on = False
        self._brightness = 0
        self.async_write_ha_state()
