"""Fuel type selector — which fuel the dashboard card shows."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import PetrolmateConfigEntry
from .const import FUELS
from .coordinator import PetrolmateCoordinator
from .entity import PetrolmateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PetrolmateConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FuelSelect(entry.runtime_data)])


class FuelSelect(PetrolmateEntity, SelectEntity, RestoreEntity):
    _attr_name = "Fuel type"
    _attr_icon = "mdi:gas-station"

    def __init__(self, coordinator: PetrolmateCoordinator) -> None:
        super().__init__(coordinator, "fuel_type")
        self._codes = {FUELS[f]["name"]: f for f in coordinator.fuels}
        self._attr_options = list(self._codes)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in self._codes:
            self.coordinator.selected_fuel = self._codes[last.state]

    @property
    def current_option(self) -> str | None:
        return FUELS.get(self.coordinator.selected_fuel, {}).get("name")

    @property
    def extra_state_attributes(self) -> dict:
        # lets the card map the option back to the fuel code / sensor
        return {"fuel": self.coordinator.selected_fuel, "codes": self._codes}

    async def async_select_option(self, option: str) -> None:
        self.coordinator.selected_fuel = self._codes[option]
        self.coordinator.async_filters_changed()
