"""Refresh button — re-query Petrolmate now."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PetrolmateConfigEntry
from .coordinator import PetrolmateCoordinator
from .entity import PetrolmateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PetrolmateConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([RefreshButton(entry.runtime_data)])


class RefreshButton(PetrolmateEntity, ButtonEntity):
    _attr_name = "Refresh"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: PetrolmateCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
