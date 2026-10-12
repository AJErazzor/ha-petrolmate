"""Switches: one per fuel brand (BP, Shell, Ampol, …), an Any switch, and one per discount."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import PetrolmateConfigEntry
from .const import FUELS, NETWORKS
from .coordinator import PetrolmateCoordinator
from .entity import PetrolmateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PetrolmateConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities(
        [NetworkSwitch(c, net) for net in c.networks]
        + [AnyBrandSwitch(c)]
        + [DiscountSwitch(c, d) for d in c.discounts]
    )


class NetworkSwitch(PetrolmateEntity, SwitchEntity, RestoreEntity):
    """Include stations selling this fuel brand."""

    _attr_icon = "mdi:gas-station-outline"

    def __init__(self, coordinator: PetrolmateCoordinator, network: str) -> None:
        # unique id keeps the old "network" key so existing entities carry over
        super().__init__(coordinator, f"network_{network}")
        self.network = network
        self._attr_name = NETWORKS[network]["name"]

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
            "label": NETWORKS[self.network]["name"],
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


class AnyBrandSwitch(PetrolmateEntity, SwitchEntity, RestoreEntity):
    """Ignore the fuel brand ticks and count every station — for road trips."""

    _attr_icon = "mdi:gas-station"
    _attr_name = "Any brand"

    def __init__(self, coordinator: PetrolmateCoordinator) -> None:
        super().__init__(coordinator, "any_brand")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        self.coordinator.any_brand = bool(last and last.state == "on")

    @property
    def is_on(self) -> bool:
        return self.coordinator.any_brand

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"any_brand": True}

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.any_brand = True
        self.coordinator.async_filters_changed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.any_brand = False
        self.coordinator.async_filters_changed()


class DiscountSwitch(PetrolmateEntity, SwitchEntity, RestoreEntity):
    """Apply one of My Discounts — switch it on while you hold the docket/voucher. Off by default."""

    _attr_icon = "mdi:ticket-percent-outline"

    def __init__(self, coordinator: PetrolmateCoordinator, discount: dict[str, Any]) -> None:
        super().__init__(coordinator, f"discount_{discount['id']}")
        self.discount = discount
        self._attr_name = f"Discount {discount['name']}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state == "on":
            self.coordinator.enabled_discounts.add(self.discount["id"])

    @property
    def is_on(self) -> bool:
        return self.discount["id"] in self.coordinator.enabled_discounts

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.discount
        return {
            "discount": d["id"],
            "label": d["name"],
            "cents": d.get("cents"),
            "brands": d.get("brands") or [],
            "fuels": [FUELS[f]["name"] for f in d.get("fuels") or [] if f in FUELS] or "all",
            "stacks": bool(d.get("stacks")),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.enabled_discounts.add(self.discount["id"])
        self.coordinator.async_filters_changed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.enabled_discounts.discard(self.discount["id"])
        self.coordinator.async_filters_changed()
