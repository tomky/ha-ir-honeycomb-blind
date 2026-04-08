"""Binary sensor platform for IR Honeycomb Blind integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLIND_NAME,
    DOMAIN,
    ENTITY_SUFFIX_IS_MOVING,
)
from .coordinator import HoneycombBlindCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IR Honeycomb Blind binary sensor entities."""
    coordinator: HoneycombBlindCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([HoneycombBlindMovingSensor(coordinator, entry)])


class HoneycombBlindMovingSensor(BinarySensorEntity):
    """Binary sensor indicating if the blind is moving."""

    _attr_device_class = BinarySensorDeviceClass.MOVING
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._blind_name = entry.data.get(CONF_BLIND_NAME, "Honeycomb Blind")

        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_IS_MOVING}"
        self._attr_translation_key = "is_moving"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self._blind_name,
            manufacturer="Generic",
            model="IR Honeycomb Blind",
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        self.async_on_remove(
            self._coordinator.add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the blind is moving."""
        return self._coordinator.is_moving
