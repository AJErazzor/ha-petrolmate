"""Data coordinator for Petrolmate: fetches nearby stations and ranks them."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
import logging
import math
import time
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_LIMIT,
    API_TIMEOUT,
    API_URL,
    CONF_BRANDS_PREFIX,
    CONF_DISCOUNTS,
    CONF_FUELS,
    CONF_LOCATION_ENTITY,
    CONF_MOVE_DISTANCE,
    CONF_NETWORKS,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    CONF_STATES,
    DEFAULT_FUELS,
    DEFAULT_LOCATION_ENTITY,
    DEFAULT_MOVE_DISTANCE,
    DEFAULT_NETWORKS,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUELS,
    NETWORKS,
)

_LOGGER = logging.getLogger(__name__)

MAX_LIST = 10  # stations kept per list; the card shows as many as its `count` asks for
MIN_MOVE_REFRESH_SECONDS = 120  # don't re-query more often than this when moving


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def split_brands(value: list[str] | None) -> list[str]:
    """Brand list without blanks or stray spaces."""
    return [b for b in (x.strip() for x in value or []) if b]


async def async_detect_state(hass: HomeAssistant, lat: float, lng: float) -> str | None:
    """State of the nearest station to a point (the API tags each station), for setup defaults."""
    try:
        async with asyncio.timeout(API_TIMEOUT):
            resp = await async_get_clientsession(hass).get(
                API_URL, params={"lat": f"{lat:.6f}", "lng": f"{lng:.6f}", "radius": 25000, "limit": 1}
            )
            payload = await resp.json(content_type=None)
        return (payload.get("stations") or [{}])[0].get("state")
    except (aiohttp.ClientError, TimeoutError, ValueError, AttributeError):
        return None


def maps_url(lat: float, lng: float) -> str:
    """Apple Maps driving directions from the current location (legacy ?daddr= only drops a pin on iOS)."""
    return f"https://maps.apple.com/directions?destination={lat},{lng}&mode=driving"


def google_maps_url(lat: float, lng: float) -> str:
    """Google Maps driving directions — opens the Google Maps app on Android."""
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"


@dataclass
class PetrolmateData:
    """Result of one API fetch."""

    stations: list[dict[str, Any]]
    latitude: float
    longitude: float
    fetched: float = field(default_factory=time.time)


class PetrolmateCoordinator(DataUpdateCoordinator[PetrolmateData]):
    """Fetches stations around the configured location entity."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        conf = {**entry.data, **entry.options}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.location_entity: str = conf.get(CONF_LOCATION_ENTITY) or DEFAULT_LOCATION_ENTITY
        self.radius_km: float = conf.get(CONF_RADIUS, DEFAULT_RADIUS)
        self.move_distance: float = conf.get(CONF_MOVE_DISTANCE, DEFAULT_MOVE_DISTANCE)
        self.fuels: list[str] = [f for f in conf.get(CONF_FUELS, DEFAULT_FUELS) if f in FUELS]
        self.networks: list[str] = [n for n in conf.get(CONF_NETWORKS, DEFAULT_NETWORKS) if n in NETWORKS]
        # network → upper-cased station brands
        self.network_brands: dict[str, list[str]] = {}
        for net in self.networks:
            brands = conf.get(f"{CONF_BRANDS_PREFIX}{net}")
            brands = NETWORKS[net]["brands"] if brands is None else split_brands(brands)
            self.network_brands[net] = [b.upper() for b in brands]
        self.states: list[str] = conf.get(CONF_STATES) or []
        # discounts: {id, name, cents, brands, fuels ([] = all), stacks}
        self.discounts: list[dict[str, Any]] = [d for d in conf.get(CONF_DISCOUNTS) or [] if d.get("id")]
        # runtime filter state, driven by the switch/select entities
        self.enabled_networks: set[str] = set(self.networks)
        self.any_brand: bool = False
        self.other_brands: bool = False  # stations whose brand isn't assigned to any fuel brand
        self.enabled_discounts: set[str] = set()
        self.selected_fuel: str = self.fuels[0] if self.fuels else "DIESEL"
        self.version: str | None = None  # integration version, shown on the device page
        self._session = async_get_clientsession(hass)

    # ---- location -------------------------------------------------------

    def _location(self) -> tuple[float, float]:
        state = self.hass.states.get(self.location_entity)
        if state is not None:
            lat, lng = state.attributes.get("latitude"), state.attributes.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                return float(lat), float(lng)
        # entity missing or has no GPS (e.g. app restarted) → home
        return self.hass.config.latitude, self.hass.config.longitude

    @callback
    def async_track_movement(self) -> None:
        """Re-query when the location entity has moved far enough."""

        @callback
        def _moved(event: Event[EventStateChangedData]) -> None:
            new = event.data["new_state"]
            if new is None or self.data is None:
                return
            lat, lng = new.attributes.get("latitude"), new.attributes.get("longitude")
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                return
            if time.time() - self.data.fetched < MIN_MOVE_REFRESH_SECONDS:
                return
            if _distance_m(lat, lng, self.data.latitude, self.data.longitude) >= self.move_distance:
                self.hass.async_create_task(self.async_request_refresh())

        self.config_entry.async_on_unload(
            async_track_state_change_event(self.hass, [self.location_entity], _moved)
        )

    # ---- fetch ----------------------------------------------------------

    async def _async_update_data(self) -> PetrolmateData:
        lat, lng = self._location()
        params = {
            "lat": f"{lat:.6f}",
            "lng": f"{lng:.6f}",
            "radius": int(min(max(self.radius_km, 1), 25) * 1000),
            "limit": API_LIMIT,
        }
        try:
            async with asyncio.timeout(API_TIMEOUT):
                resp = await self._session.get(API_URL, params=params)
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Petrolmate request failed: {err}") from err
        if not isinstance(payload, dict) or not payload.get("success"):
            raise UpdateFailed(f"Petrolmate returned an unexpected response: {str(payload)[:200]}")
        return PetrolmateData(stations=payload.get("stations") or [], latitude=lat, longitude=lng)

    # ---- ranking --------------------------------------------------------

    def network_of(self, brand: str | None) -> str | None:
        b = (brand or "").upper()
        for net, brands in self.network_brands.items():
            if b in brands:
                return net
        return None

    def seen_brands(self) -> Counter[str]:
        """Station brands in the latest search, with how many stations each."""
        return Counter(s.get("brand") for s in (self.data.stations if self.data else []) if s.get("brand"))

    def discount_for(self, brand: str | None, fuel: str) -> tuple[float, list[str]]:
        """Cents off at a station: every stacking discount plus the best single non-stacking one."""
        b = (brand or "").upper()
        stack, single = [], None
        for d in self.discounts:
            if d["id"] not in self.enabled_discounts or not d.get("cents"):
                continue
            if b not in {x.upper() for x in d.get("brands") or []}:
                continue
            if d.get("fuels") and fuel not in d["fuels"]:
                continue
            if d.get("stacks"):
                stack.append(d)
            elif single is None or d["cents"] > single["cents"]:
                single = d
        used = stack + ([single] if single else [])
        return round(sum(d["cents"] for d in used), 1), [d["name"] for d in used]

    def rows(self, fuel: str) -> list[dict[str, Any]]:
        """One row per station selling `fuel` (cheapest matching code), sorted by price after discounts, then distance."""
        if self.data is None:
            return []
        codes = FUELS.get(fuel, FUELS["DIESEL"])["codes"]
        out = []
        for s in self.data.stations:
            best = None
            for f in s.get("fuels") or []:
                p = f.get("price")
                if f.get("type") in codes and isinstance(p, (int, float)) and p > 0:
                    if best is None or p < best["price"]:
                        best = f
            if best is None:
                continue
            net = self.network_of(s.get("brand"))
            off, names = self.discount_for(s.get("brand"), fuel)
            out.append({
                "price": round(best["price"] - off, 1),
                "pump_price": best["price"],
                "discount": off,
                "discounts": names,
                "brand": s.get("brand"),
                "network": net,
                "station": s.get("name"),
                "address": f"{s.get('address', '')}, {s.get('suburb', '')}".strip(", "),
                "state": s.get("state"),
                "km": round((s.get("distance_m") or 0) / 1000, 1),
                "updated": best.get("updated"),  # UTC, no zone suffix
                "latitude": s.get("lat"),
                "longitude": s.get("lng"),
                "maps": maps_url(s.get("lat"), s.get("lng")),
                "maps_google": google_maps_url(s.get("lat"), s.get("lng")),
                # one of your ticked fuel brands, an unassigned brand with Other on, or anything with Any on
                "mine": self.any_brand or (net in self.enabled_networks if net else self.other_brands),
            })
        out.sort(key=lambda r: (r["price"], r["km"]))
        return out

    def summary(self, fuel: str) -> dict[str, Any]:
        rows = self.rows(fuel)
        mine = [r for r in rows if r["mine"]]
        closest = sorted(mine, key=lambda r: (r["km"], r["price"]))
        return {
            "top": mine[:MAX_LIST],
            "closest": closest[:MAX_LIST],
            "cheapest_any_brand": rows[0] if rows else None,
        }

    @callback
    def async_filters_changed(self) -> None:
        """Push recalculated values to entities without a new API call."""
        self.async_update_listeners()
