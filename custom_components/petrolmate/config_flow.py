"""Config and options flow for Petrolmate."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BRANDS_PREFIX,
    CONF_FUELS,
    CONF_LOCATION_ENTITY,
    CONF_MOVE_DISTANCE,
    CONF_NETWORKS,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    DEFAULT_FUELS,
    DEFAULT_LOCATION_ENTITY,
    DEFAULT_MOVE_DISTANCE,
    DEFAULT_NAME,
    DEFAULT_NETWORKS,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUELS,
    NETWORKS,
)


def _search_schema(d: dict[str, Any]) -> dict:
    """Fields shared by setup and options: where to search and what for."""
    return {
        vol.Required(CONF_LOCATION_ENTITY, default=d.get(CONF_LOCATION_ENTITY, DEFAULT_LOCATION_ENTITY)):
            selector.EntitySelector(selector.EntitySelectorConfig(domain=["device_tracker", "person", "zone"])),
        vol.Required(CONF_RADIUS, default=d.get(CONF_RADIUS, DEFAULT_RADIUS)):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=1, max=25, step=1, unit_of_measurement="km", mode=selector.NumberSelectorMode.SLIDER)),
        vol.Required(CONF_FUELS, default=d.get(CONF_FUELS, DEFAULT_FUELS)):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=k, label=v["name"]) for k, v in FUELS.items()],
                multiple=True, mode=selector.SelectSelectorMode.LIST)),
        vol.Required(CONF_NETWORKS, default=d.get(CONF_NETWORKS, DEFAULT_NETWORKS)):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=k, label=v["name"]) for k, v in NETWORKS.items()],
                multiple=True, mode=selector.SelectSelectorMode.LIST)),
    }


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors = {}
    if not user_input.get(CONF_FUELS):
        errors[CONF_FUELS] = "no_fuels"
    if not user_input.get(CONF_NETWORKS):
        errors[CONF_NETWORKS] = "no_networks"
    return errors


class PetrolmateConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                name = user_input.pop(CONF_NAME, DEFAULT_NAME) or DEFAULT_NAME
                return self.async_create_entry(title=name, data={}, options=user_input)
        defaults = user_input or {}
        schema = vol.Schema({vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
                             **_search_schema(defaults)})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PetrolmateOptionsFlow:
        return PetrolmateOptionsFlow()


class PetrolmateOptionsFlow(OptionsFlow):
    """Step 1: search settings. Step 2: which station brands count for each chosen card network."""

    def __init__(self) -> None:
        self._pending: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                self._pending = user_input
                return await self.async_step_brands()
        d = {**current, **(user_input or {})}
        schema = vol.Schema({
            **_search_schema(d),
            vol.Required(CONF_SCAN_INTERVAL, default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)):
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=10, max=360, step=5, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_MOVE_DISTANCE, default=d.get(CONF_MOVE_DISTANCE, DEFAULT_MOVE_DISTANCE)):
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=100, max=10000, step=100, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_brands(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        nets = self._pending[CONF_NETWORKS]
        if user_input is not None:
            return self.async_create_entry(data={**self._pending, **user_input})
        fields = {}
        for net in nets:
            key = f"{CONF_BRANDS_PREFIX}{net}"
            default = current.get(key)
            if default is None:
                default = ", ".join(NETWORKS[net]["brands"])
            elif isinstance(default, list):
                default = ", ".join(default)
            fields[vol.Required(key, default=default)] = selector.TextSelector()
        return self.async_show_form(
            step_id="brands",
            data_schema=vol.Schema(fields),
            description_placeholders={"networks": ", ".join(NETWORKS[n]["name"] for n in nets)},
        )
