"""Sensors: cheapest price per fuel (with top3 / closest3 lists), plus a station count."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PetrolmateConfigEntry
from .const import FUELS, NETWORKS
from .coordinator import PetrolmateCoordinator
from .entity import PetrolmateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PetrolmateConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [CheapestFuelSensor(coordinator, fuel) for fuel in coordinator.fuels]
    entities.append(StationsSensor(coordinator))
    async_add_entities(entities)


class CheapestFuelSensor(PetrolmateEntity, SensorEntity):
    """Cheapest price (after your discounts) for one fuel at the ticked fuel brands, in c/L."""

    _attr_native_unit_of_measurement = "c/L"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:gas-station"
    # lists change constantly and are only useful live — keep them out of the recorder
    _unrecorded_attributes = frozenset({"top3", "closest3", "cheapest_any_brand", "maps", "maps_google", "updated"})

    def __init__(self, coordinator: PetrolmateCoordinator, fuel: str) -> None:
        super().__init__(coordinator, f"cheapest_{fuel.lower()}")
        self.fuel = fuel
        self._attr_name = f"Cheapest {FUELS[fuel]['name']}"

    @property
    def _summary(self) -> dict[str, Any]:
        return self.coordinator.summary(self.fuel)

    @property
    def native_value(self) -> float | None:
        top = self._summary["top3"]
        return top[0]["price"] if top else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        s = self._summary
        best = s["top3"][0] if s["top3"] else None
        c = self.coordinator
        return {
            "fuel": self.fuel,
            "fuel_name": FUELS[self.fuel]["name"],
            "station": best and best["station"],
            "brand": best and best["brand"],
            "network": best and best["network"],
            "address": best and best["address"],
            "distance_km": best and best["km"],
            "updated": best and best["updated"],
            "pump_price": best and best["pump_price"],
            "discount": best and best["discount"],
            "discounts": best and best["discounts"],
            "maps": best and best["maps"],
            "maps_google": best and best["maps_google"],
            # latitude/longitude put the cheapest station on a map card
            "latitude": best and best["latitude"],
            "longitude": best and best["longitude"],
            "top3": s["top3"],
            "closest3": s["closest3"],
            "cheapest_any_brand": s["cheapest_any_brand"],
            "networks": sorted(c.enabled_networks),
            "any_brand": c.any_brand,
            "other_brands": c.other_brands,
            "network_colors": {n: NETWORKS[n]["color"] for n in c.networks},
        }


class StationsSensor(PetrolmateEntity, SensorEntity):
    """How many stations the last search returned, and how far it reached."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:map-marker-radius"
    _attr_native_unit_of_measurement = "stations"
    _attr_name = "Stations searched"

    def __init__(self, coordinator: PetrolmateCoordinator) -> None:
        super().__init__(coordinator, "stations")

    @property
    def native_value(self) -> int | None:
        return len(self.coordinator.data.stations) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        if not d:
            return {}
        dists = [s.get("distance_m") or 0 for s in d.stations]
        return {
            "reach_km": round(max(dists) / 1000, 1) if dists else None,
            "radius_km": self.coordinator.radius_km,
            "location_entity": self.coordinator.location_entity,
            "searched_latitude": d.latitude,
            "searched_longitude": d.longitude,
        }
