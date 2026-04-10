"""Config flow for IR Honeycomb Blind integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BLIND_NAME,
    CONF_DEBOUNCE_DELAY,
    CONF_ENABLE_COMBINED_COVER,
    CONF_ENABLE_SEPARATE_COVERS,
    CONF_IR_CODE_B_DN,
    CONF_IR_CODE_B_UP,
    CONF_IR_CODE_STOP,
    CONF_IR_CODE_T_DN,
    CONF_IR_CODE_T_UP,
    CONF_IR_REPEAT,
    CONF_IR_REPEAT_DELAY,
    CONF_REALTIME_POSITION,
    CONF_REMOTE_ENTITY,
    CONF_T_CLOSE,
    CONF_T_OPEN,
    DEFAULT_DEBOUNCE_DELAY,
    DEFAULT_ENABLE_COMBINED_COVER,
    DEFAULT_ENABLE_SEPARATE_COVERS,
    DEFAULT_IR_REPEAT,
    DEFAULT_IR_REPEAT_DELAY,
    DEFAULT_REALTIME_POSITION,
    DEFAULT_T_CLOSE,
    DEFAULT_T_OPEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class HoneycombBlindConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IR Honeycomb Blind."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input
            blind_name = user_input[CONF_BLIND_NAME]
            remote_entity = user_input[CONF_REMOTE_ENTITY]

            # Check if remote entity exists
            if not self.hass.states.get(remote_entity):
                errors["base"] = "remote_not_found"
            else:
                # Validate IR codes (must start with b64: for Broadlink)
                ir_codes_valid = True
                for key in [
                    CONF_IR_CODE_T_UP,
                    CONF_IR_CODE_T_DN,
                    CONF_IR_CODE_B_UP,
                    CONF_IR_CODE_B_DN,
                    CONF_IR_CODE_STOP,
                ]:
                    code = user_input.get(key, "")
                    if not code.startswith("b64:"):
                        errors["base"] = "invalid_ir_code"
                        ir_codes_valid = False
                        break

                if ir_codes_valid and not errors:
                    # Create unique ID based on name
                    await self.async_set_unique_id(f"{DOMAIN}_{blind_name}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=blind_name,
                        data=user_input,
                    )

        # Build schema
        data_schema = vol.Schema(
            {
                vol.Required(CONF_BLIND_NAME): str,
                vol.Required(CONF_REMOTE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Required(CONF_IR_CODE_T_UP): str,
                vol.Required(CONF_IR_CODE_T_DN): str,
                vol.Required(CONF_IR_CODE_B_UP): str,
                vol.Required(CONF_IR_CODE_B_DN): str,
                vol.Required(CONF_IR_CODE_STOP): str,
                vol.Required(CONF_T_OPEN, default=DEFAULT_T_OPEN): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=300,
                        step=0.5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_T_CLOSE, default=DEFAULT_T_CLOSE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=300,
                        step=0.5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_IR_REPEAT, default=DEFAULT_IR_REPEAT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=10,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_IR_REPEAT_DELAY, default=DEFAULT_IR_REPEAT_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=2.0,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_DEBOUNCE_DELAY, default=DEFAULT_DEBOUNCE_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.3,
                        max=5.0,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_REALTIME_POSITION, default=DEFAULT_REALTIME_POSITION
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_SEPARATE_COVERS, default=DEFAULT_ENABLE_SEPARATE_COVERS
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_COMBINED_COVER, default=DEFAULT_ENABLE_COMBINED_COVER
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return HoneycombBlindOptionsFlow(config_entry)


class HoneycombBlindOptionsFlow(OptionsFlow):
    """Handle options flow for IR Honeycomb Blind."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate IR codes
            ir_codes_valid = True
            for key in [
                CONF_IR_CODE_T_UP,
                CONF_IR_CODE_T_DN,
                CONF_IR_CODE_B_UP,
                CONF_IR_CODE_B_DN,
                CONF_IR_CODE_STOP,
            ]:
                code = user_input.get(key, "")
                if code and not code.startswith("b64:"):
                    errors["base"] = "invalid_ir_code"
                    ir_codes_valid = False
                    break

            if ir_codes_valid and not errors:
                # Merge with existing data
                new_data = {**self._config_entry.data, **user_input}
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})

        # Pre-fill with current values
        current = self._config_entry.data

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_REMOTE_ENTITY,
                    default=current.get(CONF_REMOTE_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Required(
                    CONF_IR_CODE_T_UP,
                    default=current.get(CONF_IR_CODE_T_UP),
                ): str,
                vol.Required(
                    CONF_IR_CODE_T_DN,
                    default=current.get(CONF_IR_CODE_T_DN),
                ): str,
                vol.Required(
                    CONF_IR_CODE_B_UP,
                    default=current.get(CONF_IR_CODE_B_UP),
                ): str,
                vol.Required(
                    CONF_IR_CODE_B_DN,
                    default=current.get(CONF_IR_CODE_B_DN),
                ): str,
                vol.Required(
                    CONF_IR_CODE_STOP,
                    default=current.get(CONF_IR_CODE_STOP),
                ): str,
                vol.Required(
                    CONF_T_OPEN,
                    default=current.get(CONF_T_OPEN, DEFAULT_T_OPEN),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=300,
                        step=0.5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_T_CLOSE,
                    default=current.get(CONF_T_CLOSE, DEFAULT_T_CLOSE),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=300,
                        step=0.5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_IR_REPEAT,
                    default=current.get(CONF_IR_REPEAT, DEFAULT_IR_REPEAT),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=10,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_IR_REPEAT_DELAY,
                    default=current.get(CONF_IR_REPEAT_DELAY, DEFAULT_IR_REPEAT_DELAY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=2.0,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_DEBOUNCE_DELAY,
                    default=current.get(CONF_DEBOUNCE_DELAY, DEFAULT_DEBOUNCE_DELAY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.3,
                        max=5.0,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_REALTIME_POSITION,
                    default=current.get(CONF_REALTIME_POSITION, DEFAULT_REALTIME_POSITION),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_SEPARATE_COVERS,
                    default=current.get(CONF_ENABLE_SEPARATE_COVERS, DEFAULT_ENABLE_SEPARATE_COVERS),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_COMBINED_COVER,
                    default=current.get(CONF_ENABLE_COMBINED_COVER, DEFAULT_ENABLE_COMBINED_COVER),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
