"""Base entity for Petrolmate."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import PetrolmateCoordinator


class PetrolmateEntity(CoordinatorEntity[PetrolmateCoordinator]):
    """All Petrolmate entities hang off one service device per config entry."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: PetrolmateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=coordinator.version,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://petrolmate.com.au/home-assistant",
        )
