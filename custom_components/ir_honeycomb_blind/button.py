"""Button platform for IR Honeycomb Blind integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_BLIND_NAME, DOMAIN
from .coordinator import HoneycombBlindCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IR Honeycomb Blind button entities."""
    coordinator: HoneycombBlindCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([HoneycombBlindCalibrateButton(coordinator, entry)])


class HoneycombBlindCalibrateButton(ButtonEntity):
    """Button entity to calibrate the honeycomb blind."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:crosshairs"

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calibrate button."""
        self._coordinator = coordinator
        self._entry = entry
        self._blind_name = entry.data.get(CONF_BLIND_NAME, "Honeycomb Blind")

        self._attr_unique_id = f"{entry.entry_id}_calibrate"
        self._attr_translation_key = "calibrate"

        # Device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self._blind_name,
            manufacturer="Generic",
            model="IR Honeycomb Blind",
        )

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Calibrate"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Calibrating blind: %s", self._blind_name)
        await self._coordinator.async_calibrate()
