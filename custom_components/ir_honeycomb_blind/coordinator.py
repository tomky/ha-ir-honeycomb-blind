"""Coordinator for IR Honeycomb Blind integration."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_LAST_CALIBRATION,
    ATTR_POS,
    ATTR_RATIO,
    ATTR_TOP_POS,
    CONF_BLIND_NAME,
    CONF_DEBOUNCE_DELAY,
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
    DEFAULT_IR_REPEAT,
    DEFAULT_IR_REPEAT_DELAY,
    DEFAULT_REALTIME_POSITION,
    DEFAULT_T_CLOSE,
    DEFAULT_T_OPEN,
    DOMAIN,
    POS_MAX,
    POS_MIN,
    REALTIME_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


@dataclass
class BlindState:
    """State of a honeycomb blind."""

    pos: float = 0.0  # Bottom rail position (0-100)
    ratio: float = 0.0  # Top rail coverage ratio (0-100)
    top_pos: float = 100.0  # Top rail position (0-100), calculated value

    # Movement state
    is_moving: bool = False
    moving_rail: str | None = None  # "bottom" or "top"
    move_start_time: float | None = None
    move_start_pos: float | None = None
    move_target_pos: float | None = None
    move_direction: int = 0  # 1 for up, -1 for down
    move_duration: float = 0.0  # Expected duration of current movement

    # Calibration tracking
    last_calibration: datetime | None = None

    # Debounce state
    target_pos: float | None = None
    target_ratio: float | None = None
    debounce_task: asyncio.Task | None = field(default=None, repr=False)
    debounce_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    execution_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    cancel_requested: bool = False

    def calculate_top_pos(self) -> float:
        """Calculate top rail position from pos and ratio."""
        return 100 - (100 - self.pos) * self.ratio / 100

    def update_top_pos(self) -> None:
        """Update top_pos based on current pos and ratio."""
        self.top_pos = self.calculate_top_pos()


class HoneycombBlindCoordinator:
    """Coordinator for a single honeycomb blind."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        ir_lock: asyncio.Lock,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self._config = entry.data
        self._name = entry.data.get(CONF_BLIND_NAME, entry.entry_id[:8])

        self._state = BlindState()
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._listeners: list[Callable[[], None]] = []
        # Shared IR lock - prevents concurrent IR sends from blinds using the same remote
        self._ir_lock = ir_lock

    def _log(self, level: int, msg: str, *args) -> None:
        """Log with blind name prefix."""
        _LOGGER.log(level, "[%s] " + msg, self._name, *args)

    @property
    def config(self) -> dict:
        """Return the configuration."""
        return self._config

    @property
    def state(self) -> BlindState:
        """Return the current state."""
        return self._state

    @property
    def pos(self) -> float:
        """Return the bottom rail position."""
        return self._state.pos

    @property
    def ratio(self) -> float:
        """Return the top rail ratio."""
        return self._state.ratio

    @property
    def top_pos(self) -> float:
        """Return the top rail position."""
        return self._state.top_pos

    @property
    def is_moving(self) -> bool:
        """Return if the blind is moving."""
        return self._state.is_moving

    @property
    def t_open(self) -> float:
        """Return the time to fully open."""
        return self._config.get(CONF_T_OPEN, DEFAULT_T_OPEN)

    @property
    def t_close(self) -> float:
        """Return the time to fully close."""
        return self._config.get(CONF_T_CLOSE, DEFAULT_T_CLOSE)

    @property
    def debounce_delay(self) -> float:
        """Return the debounce delay."""
        return self._config.get(CONF_DEBOUNCE_DELAY, DEFAULT_DEBOUNCE_DELAY)

    @property
    def realtime_position_enabled(self) -> bool:
        """Return if realtime position update is enabled."""
        return self._config.get(CONF_REALTIME_POSITION, DEFAULT_REALTIME_POSITION)

    async def async_load(self) -> None:
        """Load state from storage."""
        data = await self._store.async_load()
        if data:
            self._state.pos = data.get(ATTR_POS, 0.0)
            self._state.ratio = data.get(ATTR_RATIO, 0.0)
            self._state.top_pos = data.get(ATTR_TOP_POS, 100.0)
            # Load last calibration time
            if ATTR_LAST_CALIBRATION in data and data[ATTR_LAST_CALIBRATION]:
                try:
                    self._state.last_calibration = datetime.fromisoformat(
                        data[ATTR_LAST_CALIBRATION]
                    )
                except (ValueError, TypeError):
                    self._state.last_calibration = None
            self._log(
                logging.DEBUG,
                "Loaded state: pos=%s, ratio=%s, top_pos=%s",
                self._state.pos,
                self._state.ratio,
                self._state.top_pos,
            )

    async def async_save(self) -> None:
        """Save state to storage."""
        data = {
            ATTR_POS: self._state.pos,
            ATTR_RATIO: self._state.ratio,
            ATTR_TOP_POS: self._state.top_pos,
            ATTR_LAST_CALIBRATION: (
                self._state.last_calibration.isoformat()
                if self._state.last_calibration
                else None
            ),
        }
        await self._store.async_save(data)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Add a state change listener."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        """Notify all listeners of state change."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                self._log(logging.ERROR, "Error notifying listener: %s", e)

    async def _send_ir(self, ir_code: str) -> None:
        """Send IR command via remote entity."""
        async with self._ir_lock:
            remote_entity = self._config[CONF_REMOTE_ENTITY]
            num_repeats = int(self._config.get(CONF_IR_REPEAT, DEFAULT_IR_REPEAT))
            delay_secs = float(self._config.get(CONF_IR_REPEAT_DELAY, DEFAULT_IR_REPEAT_DELAY))

            self._log(
                logging.DEBUG,
                "Sending IR to %s: %s... (repeats=%s)",
                remote_entity,
                ir_code[:30],
                num_repeats,
            )

            try:
                await self.hass.services.async_call(
                    "remote",
                    "send_command",
                    {
                        "command": ir_code,
                        "num_repeats": num_repeats,
                        "delay_secs": delay_secs,
                    },
                    target={"entity_id": remote_entity},
                    blocking=True,
                )
            except Exception as e:
                self._log(logging.ERROR, "Failed to send IR command: %s", e)
                raise

    async def _send_stop(self) -> None:
        """Send stop IR command."""
        ir_code = self._config[CONF_IR_CODE_STOP]
        await self._send_ir(ir_code)

    async def _interruptible_sleep(self, duration: float) -> bool:
        """Sleep for duration, checking cancel_requested every 0.5s.

        Returns True if sleep completed, False if interrupted.
        """
        interval = 0.5
        remaining = duration
        while remaining > 0:
            if self._state.cancel_requested:
                return False
            await asyncio.sleep(min(interval, remaining))
            remaining -= interval
        return True

    def _calculate_move_time(self, distance: float, direction: int) -> float:
        """Calculate movement time for a given distance."""
        if direction > 0:  # Moving up
            return abs(distance) / 100 * self.t_open
        else:  # Moving down
            return abs(distance) / 100 * self.t_close

    def _estimate_current_position(self) -> float | None:
        """Estimate current position based on elapsed movement time."""
        if not self._state.is_moving or self._state.move_start_time is None:
            return None

        elapsed = time.time() - self._state.move_start_time
        start_pos = self._state.move_start_pos
        target_pos = self._state.move_target_pos
        direction = self._state.move_direction

        if start_pos is None or target_pos is None:
            return None

        distance = abs(target_pos - start_pos)
        move_time = self._calculate_move_time(distance, direction)

        if move_time <= 0:
            return target_pos

        progress = min(elapsed / move_time, 1.0)
        estimated = start_pos + direction * distance * progress

        return max(POS_MIN, min(POS_MAX, estimated))

    def get_estimated_position(self) -> tuple[float | None, str | None]:
        """Get estimated position for the currently moving rail.

        Returns:
            Tuple of (estimated_position, rail_name) where rail_name is "bottom" or "top".
            Returns (None, None) if not moving.
        """
        if not self._state.is_moving:
            return None, None
        estimated = self._estimate_current_position()
        return estimated, self._state.moving_rail

    def get_time_remaining(self) -> float | None:
        """Get estimated remaining movement time in seconds.

        Returns:
            Remaining time in seconds, or None if not moving.
        """
        if not self._state.is_moving or self._state.move_start_time is None:
            return None
        if self._state.move_duration <= 0:
            return None
        elapsed = time.time() - self._state.move_start_time
        remaining = self._state.move_duration - elapsed
        return max(0.0, remaining)

    async def _interruptible_sleep(self, seconds: float, check_interval: float = 0.1) -> bool:
        """Sleep that can be interrupted by cancel_requested flag.

        Returns True if completed, False if interrupted.
        """
        elapsed = 0.0
        last_notify = 0.0
        notify_interval = REALTIME_UPDATE_INTERVAL

        while elapsed < seconds:
            if self._state.cancel_requested:
                self._log(logging.DEBUG, "Sleep interrupted by cancel request")
                return False
            sleep_time = min(check_interval, seconds - elapsed)
            await asyncio.sleep(sleep_time)
            elapsed += sleep_time

            # Notify listeners periodically for realtime position updates
            if self.realtime_position_enabled and elapsed - last_notify >= notify_interval:
                self._notify_listeners()
                last_notify = elapsed

        return True

    async def _do_interrupt(self) -> None:
        """Actually perform the interrupt - send stop and update position."""
        self._log(logging.DEBUG, "Performing interrupt")

        # Send stop command
        await self._send_stop()

        # Estimate current position
        estimated_pos = self._estimate_current_position()

        if estimated_pos is not None:
            if self._state.moving_rail == "bottom":
                self._state.pos = round(estimated_pos, 1)
                self._state.update_top_pos()
                self._log(logging.DEBUG, "Estimated bottom pos: %s", self._state.pos)
            elif self._state.moving_rail == "top":
                self._state.top_pos = round(estimated_pos, 1)
                # Reverse-calculate ratio from top_pos
                if 100 - self._state.pos > 0:
                    self._state.ratio = round(
                        (100 - self._state.top_pos) / (100 - self._state.pos) * 100, 1
                    )
                    self._state.ratio = max(0, min(100, self._state.ratio))
                self._log(logging.DEBUG, "Estimated top pos: %s, ratio: %s",
                         self._state.top_pos, self._state.ratio)

        # Reset movement state
        self._state.is_moving = False
        self._state.moving_rail = None
        self._state.move_start_time = None
        self._state.move_start_pos = None
        self._state.move_target_pos = None
        self._state.move_direction = 0
        self._state.move_duration = 0.0

        await self.async_save()
        self._notify_listeners()

    async def _move_rail(
        self,
        rail: str,
        target: float,
        ir_code_up: str,
        ir_code_dn: str,
    ) -> bool:
        """Move a rail to target position. Returns True if completed, False if interrupted."""
        current = self._state.pos if rail == "bottom" else self._state.top_pos
        target = max(POS_MIN, min(POS_MAX, target))

        delta = target - current
        if abs(delta) < 0.5:
            self._log(logging.DEBUG, "Rail %s already at target position", rail)
            return True

        direction = 1 if delta > 0 else -1
        ir_code = ir_code_up if direction > 0 else ir_code_dn
        move_time = self._calculate_move_time(abs(delta), direction)

        self._log(
            logging.DEBUG,
            "Moving %s rail from %s to %s (dir=%s, time=%.1fs)",
            rail, current, target, direction, move_time,
        )

        # Set movement state
        self._state.is_moving = True
        self._state.moving_rail = rail
        self._state.move_start_time = time.time()
        self._state.move_start_pos = current
        self._state.move_target_pos = target
        self._state.move_direction = direction
        self._state.move_duration = move_time
        self._notify_listeners()

        # Send move command
        await self._send_ir(ir_code)

        # Wait for movement with interrupt check
        completed = await self._interruptible_sleep(move_time)

        if not completed or self._state.cancel_requested:
            # Was interrupted
            await self._do_interrupt()
            return False

        # Send stop command
        await self._send_stop()

        # Update position
        # NOTE: We only update the position of the rail that actually moved.
        # - For bottom rail: don't update top_pos (physical top rail hasn't moved)
        # - For top rail: don't recalculate ratio (ratio is user's desired setting)
        # Ratio recalculation is only done in _do_interrupt when movement is interrupted.
        if rail == "bottom":
            self._state.pos = target
        else:
            self._state.top_pos = target

        # Reset movement state
        self._state.is_moving = False
        self._state.moving_rail = None
        self._state.move_start_time = None
        self._state.move_start_pos = None
        self._state.move_target_pos = None
        self._state.move_direction = 0
        self._state.move_duration = 0.0

        await self.async_save()
        self._notify_listeners()

        return True

    async def _move_bottom(self, target: float) -> bool:
        """Move bottom rail to target position."""
        return await self._move_rail(
            "bottom",
            target,
            self._config[CONF_IR_CODE_B_UP],
            self._config[CONF_IR_CODE_B_DN],
        )

    async def _move_top(self, target: float) -> bool:
        """Move top rail to target position."""
        return await self._move_rail(
            "top",
            target,
            self._config[CONF_IR_CODE_T_UP],
            self._config[CONF_IR_CODE_T_DN],
        )

    async def _execute_move(self) -> None:
        """Execute the movement based on pending targets."""
        # Use execution lock to prevent concurrent executions for this blind
        async with self._state.execution_lock:
            self._state.cancel_requested = False

            target_pos = self._state.target_pos
            target_ratio = self._state.target_ratio

            has_pos = target_pos is not None
            has_ratio = target_ratio is not None

            self._log(
                logging.INFO,
                "Executing move: target_pos=%s, target_ratio=%s",
                target_pos, target_ratio,
            )

            # Update ratio if provided
            if has_ratio:
                self._state.ratio = max(0, min(100, target_ratio))

            # NOTE: Don't clear targets here - only clear after successful completion
            # This allows targets to be preserved if a new call comes in mid-execution

            try:
                if has_pos:
                    # Position change (with or without ratio change)
                    target_pos = max(POS_MIN, min(POS_MAX, target_pos))

                    self._log(
                        logging.DEBUG,
                        "Current state: pos=%s, top_pos=%s, ratio=%s",
                        self._state.pos, self._state.top_pos, self._state.ratio,
                    )

                    # Check if bottom rail will collide with top rail
                    if target_pos > self._state.pos and target_pos >= self._state.top_pos:
                        # Need to move top rail out of the way first
                        final_top_est = 100 - (100 - target_pos) * self._state.ratio / 100
                        clearance_top = max(target_pos + 1, final_top_est)
                        clearance_top = min(POS_MAX, clearance_top)

                        self._log(logging.DEBUG, "Moving top rail for clearance to %s", clearance_top)
                        if not await self._move_top(clearance_top):
                            self._log(logging.DEBUG, "Clearance move interrupted")
                            return

                    if self._state.cancel_requested:
                        return

                    # Move bottom rail
                    self._log(logging.INFO, "Step: Moving bottom rail to %s", target_pos)
                    if not await self._move_bottom(target_pos):
                        self._log(logging.DEBUG, "Bottom move interrupted")
                        return

                    self._log(
                        logging.DEBUG,
                        "After bottom move: pos=%s, top_pos=%s",
                        self._state.pos, self._state.top_pos,
                    )

                    if self._state.cancel_requested:
                        return

                    # Adjust top rail according to ratio
                    final_top = 100 - (100 - self._state.pos) * self._state.ratio / 100
                    self._log(logging.INFO, "Step: Moving top rail to %s (ratio=%s)", final_top, self._state.ratio)
                    if not await self._move_top(final_top):
                        self._log(logging.DEBUG, "Top adjust move interrupted")
                        return

                elif has_ratio:
                    # Ratio change only
                    self._log(
                        logging.DEBUG,
                        "Current state: pos=%s, top_pos=%s, ratio=%s",
                        self._state.pos, self._state.top_pos, self._state.ratio,
                    )
                    target_top = 100 - (100 - self._state.pos) * self._state.ratio / 100

                    # Check if top rail will collide with bottom rail
                    if target_top < self._state.top_pos and target_top <= self._state.pos:
                        # Need to move bottom rail out of the way first
                        clearance_bottom = max(POS_MIN, target_top - 1)

                        self._log(logging.DEBUG, "Moving bottom rail for clearance to %s", clearance_bottom)
                        if not await self._move_bottom(clearance_bottom):
                            return

                    if self._state.cancel_requested:
                        return

                    # Recalculate target after potential bottom move
                    final_target_top = 100 - (100 - self._state.pos) * self._state.ratio / 100
                    if not await self._move_top(final_target_top):
                        return

                # Clear targets only after successful completion
                self._state.target_pos = None
                self._state.target_ratio = None
                self._log(logging.INFO, "Movement completed")

            except Exception as e:
                self._log(logging.ERROR, "Error during movement: %s", e)
                # Reset movement state to prevent being stuck in "moving"
                self._state.is_moving = False
                self._state.moving_rail = None
                self._state.move_start_time = None
                self._state.move_start_pos = None
                self._state.move_target_pos = None
                self._state.move_direction = 0
                self._state.move_duration = 0.0
                self._notify_listeners()
                raise

    async def _debounce_and_execute(self) -> None:
        """Wait for debounce delay then execute movement."""
        try:
            self._log(logging.DEBUG, "Debounce started, waiting %.1fs", self.debounce_delay)
            await asyncio.sleep(self.debounce_delay)
            self._log(logging.DEBUG, "Debounce finished, executing")
            await self._execute_move()
        except asyncio.CancelledError:
            self._log(logging.DEBUG, "Debounce task cancelled")
        finally:
            self._state.debounce_task = None

    async def _cancel_debounce_task(self) -> None:
        """Cancel existing debounce task and wait for it to finish."""
        if self._state.debounce_task and not self._state.debounce_task.done():
            self._state.debounce_task.cancel()
            try:
                await self._state.debounce_task
            except asyncio.CancelledError:
                pass
            self._state.debounce_task = None

    async def async_set_position(self, position: float) -> None:
        """Set bottom rail position with debounce."""
        async with self._state.debounce_lock:
            self._log(logging.INFO, "Setting position to %s", position)

            # Request cancel if currently executing
            if self._state.execution_lock.locked():
                self._log(logging.DEBUG, "Requesting cancel of current execution")
                self._state.cancel_requested = True

            # Update target (existing target_ratio is preserved)
            self._state.target_pos = position

            # Cancel existing debounce task
            await self._cancel_debounce_task()

            # Start new debounce task
            self._state.debounce_task = asyncio.create_task(self._debounce_and_execute())

    async def async_set_ratio(self, ratio: float) -> None:
        """Set top rail ratio with debounce."""
        async with self._state.debounce_lock:
            self._log(logging.INFO, "Setting ratio to %s", ratio)

            # Request cancel if currently executing
            if self._state.execution_lock.locked():
                self._log(logging.DEBUG, "Requesting cancel of current execution")
                self._state.cancel_requested = True

            # Update target (existing target_pos is preserved)
            self._state.target_ratio = ratio

            # Cancel existing debounce task
            await self._cancel_debounce_task()

            # Start new debounce task
            self._state.debounce_task = asyncio.create_task(self._debounce_and_execute())

    async def async_stop(self) -> None:
        """Stop all movement."""
        self._log(logging.INFO, "Stop requested")

        async with self._state.debounce_lock:
            # Request cancel
            self._state.cancel_requested = True

            # Cancel debounce task
            if self._state.debounce_task and not self._state.debounce_task.done():
                self._state.debounce_task.cancel()
                try:
                    await self._state.debounce_task
                except asyncio.CancelledError:
                    pass
                self._state.debounce_task = None

            # Clear pending targets
            self._state.target_pos = None
            self._state.target_ratio = None

        # If currently moving, the cancel_requested flag will cause it to stop
        # and _do_interrupt will be called from _move_rail
        if self._state.is_moving:
            # Wait for the execution lock to be released, meaning movement has finished
            # Use a timeout to avoid waiting forever
            for _ in range(20):  # 2 seconds max
                await asyncio.sleep(0.1)
                if not self._state.is_moving:
                    break
            else:
                # Force interrupt if still moving after timeout
                if self._state.is_moving:
                    self._log(logging.WARNING, "Movement did not stop within timeout, forcing interrupt")
                    await self._do_interrupt()

    async def async_calibrate(self) -> None:
        """Calibrate the blind by moving to known positions."""
        self._log(logging.INFO, "Starting calibration")

        # Stop any current movement
        await self.async_stop()

        # Wait for execution lock
        async with self._state.execution_lock:
            self._state.cancel_requested = False

            extra_time_up = self.t_open * 1.1
            extra_time_dn = self.t_close * 1.1

            # Step 1: Move top rail to top (out of the way)
            self._log(logging.DEBUG, "Calibration: Moving top rail to top")
            await self._send_ir(self._config[CONF_IR_CODE_T_UP])
            if not await self._interruptible_sleep(extra_time_up):
                self._log(logging.INFO, "Calibration interrupted during top rail movement")
                await self._send_stop()
                return
            await self._send_stop()

            # Step 2: Move bottom rail to bottom
            self._log(logging.DEBUG, "Calibration: Moving bottom rail to bottom")
            await self._send_ir(self._config[CONF_IR_CODE_B_DN])
            if not await self._interruptible_sleep(extra_time_dn):
                self._log(logging.INFO, "Calibration interrupted during bottom rail movement")
                await self._send_stop()
                return
            await self._send_stop()

            # Reset to known state: POS=0, R=0, top_pos=100
            self._state.pos = 0.0
            self._state.ratio = 0.0
            self._state.top_pos = 100.0
            self._state.is_moving = False
            self._state.moving_rail = None
            self._state.target_pos = None
            self._state.target_ratio = None
            self._state.last_calibration = datetime.now(timezone.utc)

            await self.async_save()
            self._notify_listeners()

            self._log(logging.INFO, "Calibration completed")

    async def async_open_position(self) -> None:
        """Open bottom rail (position = 100)."""
        await self.async_set_position(POS_MAX)

    async def async_close_position(self) -> None:
        """Close bottom rail (position = 0)."""
        await self.async_set_position(POS_MIN)

    async def async_open_ratio(self) -> None:
        """Open top rail fully (ratio = 100)."""
        await self.async_set_ratio(100)

    async def async_close_ratio(self) -> None:
        """Close top rail (ratio = 0)."""
        await self.async_set_ratio(0)
