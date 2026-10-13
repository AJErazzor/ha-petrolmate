"""Config and options flow for Petrolmate."""

from __future__ import annotations

from typing import Any
import uuid

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
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
    DEFAULT_NAME,
    DEFAULT_NETWORKS,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUELS,
    NETWORKS,
    STATE_BRANDS,
    STATES,
)
from .coordinator import async_detect_state, split_brands


async def _default_states(hass: HomeAssistant) -> list[str]:
    """The state Home Assistant's home location is in, if a station nearby says so."""
    state = await async_detect_state(hass, hass.config.latitude, hass.config.longitude)
    return [state] if state in STATES else []


def _search_schema(d: dict[str, Any]) -> dict:
    """Fields shared by setup and options: where to search and what for."""
    return {
        vol.Required(CONF_LOCATION_ENTITY, default=d.get(CONF_LOCATION_ENTITY, DEFAULT_LOCATION_ENTITY)):
            selector.EntitySelector(selector.EntitySelectorConfig(domain=["device_tracker", "person", "zone"])),
        vol.Required(CONF_RADIUS, default=d.get(CONF_RADIUS, DEFAULT_RADIUS)):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=1, max=25, step=1, unit_of_measurement="km", mode=selector.NumberSelectorMode.SLIDER)),
        vol.Optional(CONF_STATES, default=d.get(CONF_STATES) or []):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=k, label=v) for k, v in STATES.items()],
                multiple=True, mode=selector.SelectSelectorMode.DROPDOWN)),
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


def _brand_picker(entry: ConfigEntry, states: list[str] | None, chosen: list[str]) -> selector.SelectSelector:
    """Station brands to pick from: already chosen, seen in the latest search (with counts), then the state lists.
    Anything else can still be typed."""
    coordinator = getattr(entry, "runtime_data", None)
    seen = coordinator.seen_brands() if coordinator else {}
    labels: dict[str, tuple[str, str]] = {}  # upper-cased name → (value, label)

    def add(name: str, note: str) -> None:
        labels.setdefault(name.upper(), (name, f"{name} · {note}" if note else name))

    for b in chosen:  # plain names: the label is also what the chip shows once picked
        add(b, "")
    for b, n in sorted(seen.items(), key=lambda x: -x[1]):
        add(b, f"{n} nearby")
    # no states picked yet → every state's list, without the state tags
    for st in states or list(STATE_BRANDS):
        for b in STATE_BRANDS.get(st, []):
            add(b, " · ".join(s for s in states or [] if b in STATE_BRANDS.get(s, [])))
    return selector.SelectSelector(selector.SelectSelectorConfig(
        options=[selector.SelectOptionDict(value=v, label=lab) for v, lab in labels.values()],
        multiple=True, custom_value=True, mode=selector.SelectSelectorMode.DROPDOWN))


class PetrolmateConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                name = user_input.pop(CONF_NAME, DEFAULT_NAME) or DEFAULT_NAME
                return self.async_create_entry(title=name, data={}, options=user_input)
        defaults = user_input or {CONF_STATES: await _default_states(self.hass)}
        schema = vol.Schema({vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
                             **_search_schema(defaults)})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PetrolmateOptionsFlow:
        return PetrolmateOptionsFlow()


class PetrolmateOptionsFlow(OptionsFlow):
    """A menu: search settings (then where each fuel brand is sold), where each fuel brand is sold, My Discounts."""

    def __init__(self) -> None:
        self._opts: dict[str, Any] | None = None
        self._only: list[str] | None = None  # fuel brands to show on the brands page (None = all)
        self._editing: str | None = None  # id of the discount being edited; None = adding

    @property
    def opts(self) -> dict[str, Any]:
        """Working copy of the options, saved in one go when a section finishes."""
        if self._opts is None:
            self._opts = {**self.config_entry.data, **self.config_entry.options}
            self._opts[CONF_DISCOUNTS] = [dict(d) for d in self._opts.get(CONF_DISCOUNTS) or []]
        return self._opts

    def _save(self) -> ConfigFlowResult:
        return self.async_create_entry(data=self.opts)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["search", "brands", "discounts"])

    # ---- search settings ----

    async def async_step_search(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                before = set(self.opts.get(CONF_NETWORKS, DEFAULT_NETWORKS))
                self.opts.update(user_input)
                # only stop at the brands page for newly ticked fuel brands, to check their defaults
                added = [n for n in user_input[CONF_NETWORKS] if n not in before]
                if not added:
                    return self._save()
                self._only = added
                return await self.async_step_brands()
        d = {**self.opts, **(user_input or {})}
        if CONF_STATES not in d:  # installs from before states existed
            d[CONF_STATES] = await _default_states(self.hass)
        schema = vol.Schema({
            **_search_schema(d),
            vol.Required(CONF_SCAN_INTERVAL, default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)):
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=10, max=360, step=5, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_MOVE_DISTANCE, default=d.get(CONF_MOVE_DISTANCE, DEFAULT_MOVE_DISTANCE)):
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=100, max=10000, step=100, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)),
        })
        return self.async_show_form(step_id="search", data_schema=schema, errors=errors)

    # ---- where each fuel brand is sold ----

    async def async_step_brands(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One section per fuel brand, each with its station brands."""
        nets = [n for n in self.opts.get(CONF_NETWORKS, DEFAULT_NETWORKS) if n in NETWORKS]
        if self._only is not None:
            nets = [n for n in nets if n in self._only]
        if user_input is not None:
            reset = user_input.get("reset")
            for net in nets:
                self.opts[f"{CONF_BRANDS_PREFIX}{net}"] = (
                    list(NETWORKS[net]["brands"]) if reset else (user_input.get(net) or {}).get("brands") or []
                )
            return self._save()
        fields = {vol.Optional("reset", default=False): selector.BooleanSelector()}
        for net in nets:
            current = self.opts.get(f"{CONF_BRANDS_PREFIX}{net}")
            chosen = NETWORKS[net]["brands"] if current is None else split_brands(current)
            fields[vol.Required(net)] = section(vol.Schema({
                vol.Optional("brands", default=chosen): _brand_picker(self.config_entry, self.opts.get(CONF_STATES), chosen),
            }), {"collapsed": False})
        return self.async_show_form(step_id="brands", data_schema=vol.Schema(fields))

    # ---- My Discounts ----

    def _discount_list(self) -> str:
        lines = []
        for d in self.opts[CONF_DISCOUNTS]:
            fuels = ", ".join(FUELS[f]["name"] for f in d.get("fuels") or [] if f in FUELS) or "all fuels"
            stacks = " · stacks" if d.get("stacks") else ""
            lines.append(f"- **{d['name']}**: {d['cents']:g}c/L at {', '.join(d.get('brands') or []) or '—'} ({fuels}){stacks}")
        return "\n".join(lines) or "_None yet._"

    async def async_step_discounts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["discount_add"]
        if self.opts[CONF_DISCOUNTS]:
            menu += ["discount_edit", "discount_delete"]
        menu.append("discount_save")
        return self.async_show_menu(step_id="discounts", menu_options=menu,
                                    description_placeholders={"list": self._discount_list()})

    async def async_step_discount_add(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._editing = None
        return await self.async_step_discount()

    async def async_step_discount_edit(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._editing = user_input["discount"]
            return await self.async_step_discount()
        return self.async_show_form(step_id="discount_edit", data_schema=vol.Schema({
            vol.Required("discount"): self._discount_choice(multiple=False),
        }))

    async def async_step_discount_delete(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            drop = set(user_input.get("discounts") or [])
            self.opts[CONF_DISCOUNTS] = [d for d in self.opts[CONF_DISCOUNTS] if d["id"] not in drop]
            return await self.async_step_discounts()
        return self.async_show_form(step_id="discount_delete", data_schema=vol.Schema({
            vol.Optional("discounts", default=[]): self._discount_choice(multiple=True),
        }))

    async def async_step_discount_save(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self._save()

    def _discount_choice(self, multiple: bool) -> selector.SelectSelector:
        return selector.SelectSelector(selector.SelectSelectorConfig(
            options=[selector.SelectOptionDict(value=d["id"], label=d["name"]) for d in self.opts[CONF_DISCOUNTS]],
            multiple=multiple, mode=selector.SelectSelectorMode.LIST))

    async def async_step_discount(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add or edit one discount, then back to the discounts menu."""
        errors: dict[str, str] = {}
        current = next((d for d in self.opts[CONF_DISCOUNTS] if d["id"] == self._editing), {})
        if user_input is not None:
            name = (user_input.get("name") or "").strip()
            if not name:
                errors["name"] = "no_name"
            elif not user_input.get("brands"):
                errors["brands"] = "no_brands"
            else:
                d = {
                    "id": current.get("id") or uuid.uuid4().hex[:8],
                    "name": name,
                    "cents": float(user_input["cents"]),
                    "brands": split_brands(user_input["brands"]),
                    "fuels": user_input.get("fuels") or [],
                    "stacks": bool(user_input.get("stacks")),
                }
                if current:
                    self.opts[CONF_DISCOUNTS] = [d if x["id"] == d["id"] else x for x in self.opts[CONF_DISCOUNTS]]
                else:
                    self.opts[CONF_DISCOUNTS].append(d)
                return await self.async_step_discounts()
        d = {**current, **(user_input or {})}
        schema = vol.Schema({
            vol.Required("name", default=d.get("name", "")): selector.TextSelector(),
            vol.Required("cents", default=d.get("cents", 4)): selector.NumberSelector(selector.NumberSelectorConfig(
                min=0.5, max=50, step=0.5, unit_of_measurement="c/L", mode=selector.NumberSelectorMode.BOX)),
            vol.Required("brands", default=d.get("brands") or []):
                _brand_picker(self.config_entry, self.opts.get(CONF_STATES), d.get("brands") or []),
            vol.Optional("fuels", default=d.get("fuels") or []): selector.SelectSelector(selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=k, label=v["name"]) for k, v in FUELS.items()],
                multiple=True, mode=selector.SelectSelectorMode.LIST)),
            vol.Optional("stacks", default=bool(d.get("stacks"))): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="discount", data_schema=schema, errors=errors)
