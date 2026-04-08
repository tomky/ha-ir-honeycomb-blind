"""Sensor platform for IR Honeycomb Blind integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLIND_NAME,
    DOMAIN,
    ENTITY_SUFFIX_LAST_CALIBRATION,
    ENTITY_SUFFIX_MOVING_RAIL,
    ENTITY_SUFFIX_TIME_REMAINING,
)
from .coordinator import HoneycombBlindCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IR Honeycomb Blind sensor entities."""
    coordinator: HoneycombBlindCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        HoneycombBlindMovingRailSensor(coordinator, entry),
        HoneycombBlindTimeRemainingSensor(coordinator, entry),
        HoneycombBlindLastCalibrationSensor(coordinator, entry),
    ])


class HoneycombBlindBaseSensor(SensorEntity):
    """Base class for Honeycomb Blind sensor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._blind_name = entry.data.get(CONF_BLIND_NAME, "Honeycomb Blind")

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


class HoneycombBlindMovingRailSensor(HoneycombBlindBaseSensor):
    """Sensor showing which rail is currently moving."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["top", "bottom", "none"]

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_MOVING_RAIL}"
        self._attr_translation_key = "moving_rail"

    @property
    def native_value(self) -> str:
        """Return the current moving rail."""
        if self._coordinator.is_moving and self._coordinator.state.moving_rail:
            return self._coordinator.state.moving_rail
        return "none"


class HoneycombBlindTimeRemainingSensor(HoneycombBlindBaseSensor):
    """Sensor showing estimated time remaining for current movement."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_TIME_REMAINING}"
        self._attr_translation_key = "time_remaining"

    @property
    def native_value(self) -> float | None:
        """Return the estimated time remaining in seconds."""
        return self._coordinator.get_time_remaining()


class HoneycombBlindLastCalibrationSensor(HoneycombBlindBaseSensor):
    """Sensor showing when the blind was last calibrated."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_LAST_CALIBRATION}"
        self._attr_translation_key = "last_calibration"

    @property
    def native_value(self) -> datetime | None:
        """Return the last calibration time."""
        return self._coordinator.state.last_calibration
