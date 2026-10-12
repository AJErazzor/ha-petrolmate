"""One switch per configured fuel card network (BP, Shell, Ampol, …)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import PetrolmateConfigEntry
from .const import NETWORKS
from .coordinator import PetrolmateCoordinator
from .entity import PetrolmateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PetrolmateConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities([NetworkSwitch(c, net) for net in c.networks])


class NetworkSwitch(PetrolmateEntity, SwitchEntity, RestoreEntity):
    """Include stations of this card network. With every network off, all networks count."""

    _attr_icon = "mdi:credit-card-outline"

    def __init__(self, coordinator: PetrolmateCoordinator, network: str) -> None:
        super().__init__(coordinator, f"network_{network}")
        self.network = network
        self._attr_name = f"{NETWORKS[network]['name']} card"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state == "off":
            self.coordinator.enabled_networks.discard(self.network)

    @property
    def is_on(self) -> bool:
        return self.network in self.coordinator.enabled_networks

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "network": self.network,
            "color": NETWORKS[self.network]["color"],
            "logo": NETWORKS[self.network].get("logo"),
            "brands": self.coordinator.network_brands.get(self.network, []),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.enabled_networks.add(self.network)
        self.coordinator.async_filters_changed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.enabled_networks.discard(self.network)
        self.coordinator.async_filters_changed()
