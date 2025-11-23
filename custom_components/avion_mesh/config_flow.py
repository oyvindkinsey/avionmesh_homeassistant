"""Config flow for Avi-on Mesh integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AvionMeshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Avi-on Mesh."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the settings YAML file path
                username = user_input.get(CONF_USERNAME, "")
                password = user_input.get(CONF_PASSWORD, "")
                import_devices = user_input.get("import_devices", True)
                import_groups = user_input.get("import_groups", True)
                exclude_in_group = user_input.get("exclude_in_group", True)
                devices_include = user_input.get("devices_include", "")
                devices_exclude = user_input.get("devices_exclude", "")
                groups_include = user_input.get("groups_include", "")
                groups_exclude = user_input.get("groups_exclude", "")
                all_import = user_input.get("all_import", False)
                all_name = user_input.get("all_name", "All Avi-on Devices")
                cap_dimming = user_input.get("cap_dimming", "")
                cap_color_temp = user_input.get("cap_color_temp", "")

                if not username:
                    errors["base"] = "missing_username"
                elif not password:
                    errors["base"] = "missing_password"

                if not errors:
                    return self.async_create_entry(
                        title=f"Avi-on Mesh ({username})",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            # Settings moved from YAML into the config entry
                            "import_devices": bool(import_devices),
                            "import_groups": bool(import_groups),
                            # single_device option removed; each device/group is its own entity
                            "exclude_in_group": bool(exclude_in_group),
                            # include/exclude lists (comma separated strings)
                            "devices_include": str(devices_include),
                            "devices_exclude": str(devices_exclude),
                            "groups_include": str(groups_include),
                            "groups_exclude": str(groups_exclude),
                            # 'all' entity options
                            "all_import": bool(all_import),
                            "all_name": str(all_name),
                            # capability overrides (comma-separated ids)
                            "cap_dimming": str(cap_dimming),
                            "cap_color_temp": str(cap_color_temp),
                        },
                    )
            except Exception as e:
                _LOGGER.error(f"Unexpected error in config flow: {e}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional("import_devices", default=True): bool,
                    vol.Optional("import_groups", default=True): bool,
                    vol.Optional("exclude_in_group", default=True): bool,
                    vol.Optional("devices_include", default=""): str,
                    vol.Optional("devices_exclude", default=""): str,
                    vol.Optional("groups_include", default=""): str,
                    vol.Optional("groups_exclude", default=""): str,
                    vol.Optional("all_import", default=False): bool,
                    vol.Optional("all_name", default="All Avi-on Devices"): str,
                    vol.Optional("cap_dimming", default=""): str,
                    vol.Optional("cap_color_temp", default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "settings_yaml_help": "Path to YAML file with Avi-on mesh configuration"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this integration."""
        return AvionMeshOptionsFlow(config_entry)


class AvionMeshOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Avi-on Mesh."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        return self.async_show_form(step_id="init")
