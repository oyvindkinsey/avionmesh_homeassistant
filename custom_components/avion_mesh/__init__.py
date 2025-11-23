"""Avi-on Mesh Mesh integration for Home Assistant."""
import asyncio
import logging
from typing import Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import Config, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .ha_service import AvionMeshService

_LOGGER = logging.getLogger(__name__)

DOMAIN = "avion_mesh"
CONF_SETTINGS_YAML = "settings_yaml"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_SETTINGS_YAML): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Avi-on Mesh integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Avi-on Mesh from a config entry."""
    _LOGGER.info("Setting up Avi-on Mesh integration")

    service = AvionMeshService(hass, entry)

    try:
        await service.async_initialize()
        hass.data[DOMAIN][entry.entry_id] = service

        # Forward entry setup to light platform
        await hass.config_entries.async_forward_entry_setups(entry, ["light"])

        _LOGGER.info("Avi-on Mesh integration setup completed successfully")
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to set up Avi-on Mesh integration: {e}")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    service: AvionMeshService = hass.data[DOMAIN][entry.entry_id]
    await service.async_shutdown()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["light"])

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
