"""IR Honeycomb Blind integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import CONF_REMOTE_ENTITY, DOMAIN
from .coordinator import HoneycombBlindCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.COVER, Platform.SENSOR]

SERVICE_CALIBRATE = "calibrate"
ATTR_ENTRY_ID = "entry_id"

# Global IR locks per remote entity (shared across all blinds using same remote)
DATA_IR_LOCKS = "ir_locks"


def get_ir_lock(hass: HomeAssistant, remote_entity: str) -> asyncio.Lock:
    """Get or create an IR lock for a remote entity."""
    ir_locks: dict[str, asyncio.Lock] = hass.data[DOMAIN].setdefault(DATA_IR_LOCKS, {})
    if remote_entity not in ir_locks:
        ir_locks[remote_entity] = asyncio.Lock()
        _LOGGER.debug("Created IR lock for remote: %s", remote_entity)
    return ir_locks[remote_entity]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IR Honeycomb Blind from a config entry."""
    _LOGGER.debug("Setting up IR Honeycomb Blind: %s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})

    # Get shared IR lock for this remote
    remote_entity = entry.data[CONF_REMOTE_ENTITY]
    ir_lock = get_ir_lock(hass, remote_entity)

    coordinator = HoneycombBlindCoordinator(hass, entry, ir_lock)
    await coordinator.async_load()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes (auto-reload)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_CALIBRATE):
        async def handle_calibrate(call: ServiceCall) -> None:
            """Handle the calibrate service call."""
            entry_id = call.data.get(ATTR_ENTRY_ID)
            if entry_id and entry_id in hass.data[DOMAIN]:
                coord = hass.data[DOMAIN][entry_id]
                if isinstance(coord, HoneycombBlindCoordinator):
                    await coord.async_calibrate()
            else:
                # Calibrate all sequentially (they may share the same remote)
                for key, coord in hass.data[DOMAIN].items():
                    if key != DATA_IR_LOCKS and isinstance(coord, HoneycombBlindCoordinator):
                        await coord.async_calibrate()

        hass.services.async_register(
            DOMAIN,
            SERVICE_CALIBRATE,
            handle_calibrate,
            schema=vol.Schema({
                vol.Optional(ATTR_ENTRY_ID): cv.string,
            }),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading IR Honeycomb Blind: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: HoneycombBlindCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Stop any ongoing movement
        await coordinator.async_stop()

    # Check if there are any remaining coordinators (excluding ir_locks dict)
    remaining_coordinators = [
        key for key in hass.data[DOMAIN]
        if key != DATA_IR_LOCKS and isinstance(hass.data[DOMAIN][key], HoneycombBlindCoordinator)
    ]

    # Unregister services and clean up if no more entries
    if not remaining_coordinators:
        if hass.services.has_service(DOMAIN, SERVICE_CALIBRATE):
            hass.services.async_remove(DOMAIN, SERVICE_CALIBRATE)
        # Clean up IR locks
        hass.data[DOMAIN].pop(DATA_IR_LOCKS, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.debug("Reloading IR Honeycomb Blind due to options change: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
