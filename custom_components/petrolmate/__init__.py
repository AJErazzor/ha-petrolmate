"""Petrolmate fuel prices: cheapest and closest fuel near a tracked location."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import PetrolmateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = "/petrolmate/petrolmate-card.js"

PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.SWITCH, Platform.BUTTON]

type PetrolmateConfigEntry = ConfigEntry[PetrolmateCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled dashboard card and load it on every dashboard — no manual resource needed."""
    version = (await async_get_integration(hass, DOMAIN)).version
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "petrolmate-card.js"), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")  # version in the URL busts browser caches on upgrade
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PetrolmateConfigEntry) -> bool:
    coordinator = PetrolmateCoordinator(hass, entry)
    # raises ConfigEntryNotReady on failure → HA retries setup with backoff
    await coordinator.async_config_entry_first_refresh()
    coordinator.async_track_movement()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PetrolmateConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: PetrolmateConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
