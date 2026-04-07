"""Cover platform for IR Honeycomb Blind integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLIND_NAME,
    CONF_ENABLE_COMBINED_COVER,
    CONF_ENABLE_SEPARATE_COVERS,
    DEFAULT_ENABLE_COMBINED_COVER,
    DEFAULT_ENABLE_SEPARATE_COVERS,
    DOMAIN,
    ENTITY_SUFFIX_COMBINED,
    ENTITY_SUFFIX_POSITION,
    ENTITY_SUFFIX_RATIO,
)
from .coordinator import HoneycombBlindCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IR Honeycomb Blind cover entities."""
    coordinator: HoneycombBlindCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CoverEntity] = []

    # Check which cover modes are enabled
    enable_separate = entry.data.get(CONF_ENABLE_SEPARATE_COVERS, DEFAULT_ENABLE_SEPARATE_COVERS)
    enable_combined = entry.data.get(CONF_ENABLE_COMBINED_COVER, DEFAULT_ENABLE_COMBINED_COVER)

    # Add separate position/ratio covers if enabled
    if enable_separate:
        entities.append(HoneycombBlindPositionCover(coordinator, entry))
        entities.append(HoneycombBlindRatioCover(coordinator, entry))

    # Add combined cover with tilt if enabled
    if enable_combined:
        entities.append(HoneycombBlindCombinedCover(coordinator, entry))

    async_add_entities(entities)


class HoneycombBlindBaseCover(CoverEntity):
    """Base class for Honeycomb Blind cover entities."""

    _attr_device_class = CoverDeviceClass.SHADE
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the cover entity."""
        self._coordinator = coordinator
        self._entry = entry
        self._blind_name = entry.data.get(CONF_BLIND_NAME, "Honeycomb Blind")

        # Device info for grouping entities
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


class HoneycombBlindPositionCover(HoneycombBlindBaseCover):
    """Cover entity for bottom rail position control."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the position cover entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_POSITION}"
        self._attr_translation_key = "position"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Position"

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._coordinator.pos <= 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "bottom"
            and self._coordinator.state.move_direction > 0
        )

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "bottom"
            and self._coordinator.state.move_direction < 0
        )

    @property
    def current_cover_position(self) -> int:
        """Return the current position of the cover."""
        # If moving and realtime position is enabled, show estimated position
        if self._coordinator.is_moving and self._coordinator.realtime_position_enabled:
            estimated, rail = self._coordinator.get_estimated_position()
            if estimated is not None and rail == "bottom":
                return round(estimated)
        return round(self._coordinator.pos)

    @property
    def icon(self) -> str:
        """Return the icon for the cover."""
        pos = self.current_cover_position  # Use current position (may be estimated)
        if pos >= 95:
            return "mdi:blinds-open"
        elif pos > 5:
            return "mdi:blinds"
        else:
            return "mdi:blinds-horizontal-closed"

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._coordinator.async_open_position()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._coordinator.async_close_position()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._coordinator.async_stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover position."""
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._coordinator.async_set_position(float(position))


class HoneycombBlindRatioCover(HoneycombBlindBaseCover):
    """Cover entity for top rail ratio control."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the ratio cover entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_RATIO}"
        self._attr_translation_key = "ratio"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Top Rail Ratio"

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed (ratio = 0)."""
        return self._coordinator.ratio <= 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening (top rail moving down = ratio increasing)."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "top"
            and self._coordinator.state.move_direction < 0
        )

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing (top rail moving up = ratio decreasing)."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "top"
            and self._coordinator.state.move_direction > 0
        )

    @property
    def current_cover_position(self) -> int:
        """Return the current position (ratio) of the cover."""
        # If moving and realtime position is enabled, calculate ratio from estimated top position
        if self._coordinator.is_moving and self._coordinator.realtime_position_enabled:
            estimated, rail = self._coordinator.get_estimated_position()
            if estimated is not None and rail == "top":
                # Convert top_pos to ratio: ratio = (100 - top_pos) / (100 - pos) * 100
                pos = self._coordinator.pos
                if 100 - pos > 0:
                    estimated_ratio = (100 - estimated) / (100 - pos) * 100
                    return round(max(0, min(100, estimated_ratio)))
        return round(self._coordinator.ratio)

    @property
    def icon(self) -> str:
        """Return the icon for the cover."""
        ratio = self.current_cover_position  # Use current position (may be estimated)
        if ratio >= 95:
            return "mdi:blinds-horizontal-closed"
        elif ratio > 5:
            return "mdi:blinds"
        else:
            return "mdi:blinds-open"

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (set ratio to 100)."""
        await self._coordinator.async_open_ratio()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (set ratio to 0)."""
        await self._coordinator.async_close_ratio()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._coordinator.async_stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover position (ratio)."""
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._coordinator.async_set_ratio(float(position))


class HoneycombBlindCombinedCover(HoneycombBlindBaseCover):
    """Combined cover entity with position and tilt control.

    Position controls the bottom rail (0-100%).
    Tilt controls the top rail ratio (0-100%, mapped to tilt angle).
    """

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT
        | CoverEntityFeature.SET_TILT_POSITION
    )

    def __init__(
        self,
        coordinator: HoneycombBlindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the combined cover entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{ENTITY_SUFFIX_COMBINED}"
        self._attr_translation_key = "combined"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Blind"

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed (position = 0)."""
        return self._coordinator.pos <= 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "bottom"
            and self._coordinator.state.move_direction > 0
        )

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return (
            self._coordinator.is_moving
            and self._coordinator.state.moving_rail == "bottom"
            and self._coordinator.state.move_direction < 0
        )

    @property
    def current_cover_position(self) -> int:
        """Return the current position of the cover (bottom rail)."""
        if self._coordinator.is_moving and self._coordinator.realtime_position_enabled:
            estimated, rail = self._coordinator.get_estimated_position()
            if estimated is not None and rail == "bottom":
                return round(estimated)
        return round(self._coordinator.pos)

    @property
    def current_cover_tilt_position(self) -> int:
        """Return the current tilt position (top rail ratio)."""
        if self._coordinator.is_moving and self._coordinator.realtime_position_enabled:
            estimated, rail = self._coordinator.get_estimated_position()
            if estimated is not None and rail == "top":
                pos = self._coordinator.pos
                if 100 - pos > 0:
                    estimated_ratio = (100 - estimated) / (100 - pos) * 100
                    return round(max(0, min(100, estimated_ratio)))
        return round(self._coordinator.ratio)

    @property
    def icon(self) -> str:
        """Return the icon for the cover."""
        pos = self.current_cover_position
        if pos >= 95:
            return "mdi:blinds-open"
        elif pos > 5:
            return "mdi:blinds"
        else:
            return "mdi:blinds-horizontal-closed"

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (position = 100)."""
        await self._coordinator.async_open_position()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (position = 0)."""
        await self._coordinator.async_close_position()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._coordinator.async_stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover position (bottom rail)."""
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._coordinator.async_set_position(float(position))

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the tilt (ratio = 100, full coverage)."""
        await self._coordinator.async_open_ratio()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the tilt (ratio = 0, no coverage)."""
        await self._coordinator.async_close_ratio()

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop tilt movement."""
        await self._coordinator.async_stop()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the tilt position (top rail ratio)."""
        tilt_position = kwargs.get(ATTR_TILT_POSITION)
        if tilt_position is not None:
            await self._coordinator.async_set_ratio(float(tilt_position))
