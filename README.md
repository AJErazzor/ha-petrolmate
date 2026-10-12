<p align="center"><img src="custom_components/petrolmate/brand/icon@2x.png" width="120" alt="Petrolmate icon"></p>

# Petrolmate Fuel Prices for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/AJErazzor/ha-petrolmate/actions/workflows/validate.yml/badge.svg)](https://github.com/AJErazzor/ha-petrolmate/actions/workflows/validate.yml)

Find the **cheapest** and the **closest** fuel near you, limited to the fuel-card networks you actually use (BP, Shell, Ampol, Caltex, …). The search follows your phone around, and a bundled dashboard card shows everything at a glance, with a map and one-tap directions.

Prices come from the free [Petrolmate API](https://petrolmate.com.au/home-assistant), which aggregates the Australian state government fuel price schemes. No API key needed.

## Features

- **Follows you:** search around a phone tracker, a person or a zone. It re-checks after you've moved (500 m by default), not on every GPS ping.
- **Your cards only:** pick your fuel-card networks, and choose which station brands count for each (for example OTR for Shell in SA, X Convenience for BP).
- **Every fuel:** Diesel, Unleaded 91, E10, Premium 95, Premium 98 and LPG, with one sensor each.
- **Cheapest and closest:** the top 3 by price and the top 3 by distance, plus the cheapest station *without* your cards, so you can see what the card costs you.
- **Filters as entities:** a fuel-type select and one switch per card network, usable from automations too. Changing them recalculates instantly with no new API call.
- **Dashboard card included:** filter chips, numbered tiles with brand logos, and a map with callouts using Home Assistant's own map tiles. Tap any station for directions: Apple Maps on iPhone, Google Maps on Android.
- **Light on your database:** the per-station lists are kept out of the recorder.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AJErazzor&repository=ha-petrolmate&category=integration)

1. In HACS, open **⋮ → Custom repositories** and add `https://github.com/AJErazzor/ha-petrolmate` with the type **Integration**.
2. Install **Petrolmate Fuel Prices** and restart Home Assistant.
3. **Refresh your browser** (on desktop, Ctrl/Cmd + Shift + R; in the app, close and reopen it) so the dashboard card loads.

### Manual

Copy `custom_components/petrolmate` into your Home Assistant `config/custom_components/` folder, then restart.

## Setup

**Settings → Devices & services → Add integration → Petrolmate**

| Option | Notes |
|---|---|
| Search around | A `device_tracker`, `person` or `zone`. Falls back to home if it has no GPS fix. |
| Search radius | 1–25 km. The API returns the nearest 50 stations, so in a city the real reach is usually 5–8 km. |
| Fuel types | One sensor is created per fuel. |
| Fuel card networks | One switch per network. |

Under **Configure** you can also set the refresh interval (default 60 min), the "refresh after moving" distance, and, on the second page, **which station brands count for each card network** (comma separated, as Petrolmate names them).

## Dashboard card

The card is served by the integration, so there's no separate resource to add.

```yaml
type: custom:petrolmate-card
```

| Option | Default | |
|---|---|---|
| `entity` | auto | The integration's `select.*_fuel_type`. Set this if you have more than one Petrolmate entry. |
| `title` | `Fuel` | |
| `map` | `true` | Show the map. |
| `map_height` | `340` | Height in pixels. |
| `maps` | `auto` | Which app opens for directions: `auto` (Apple Maps on iPhone, iPad and Mac, Google Maps everywhere else), `apple` or `google`. |
| `logos` | built in | Override a network logo, e.g. `logos: { bp: /local/bp.svg }` |

Cheapest stations are numbered **1–3** and closest stations are lettered **A–C**, on both the tiles and the map. A station on both lists shows as **1A**.

**"Custom element doesn't exist" or the card is missing from the card picker?** Restart Home Assistant, then hard-refresh the browser (Ctrl+Shift+R). It can take more than one refresh. In the companion app, use *Settings → Companion app → Debugging → Reset frontend cache*.

## Entities

For an entry called *Petrolmate*:

| Entity | |
|---|---|
| `sensor.petrolmate_cheapest_diesel` (one per fuel) | Cheapest price in c/L at your enabled networks. Attributes include `station`, `brand`, `distance_km`, `maps` / `maps_google` (Apple and Google directions links), `latitude`/`longitude`, `top3`, `closest3` and `cheapest_any_brand`. |
| `sensor.petrolmate_stations_searched` | How many stations the last search returned, and how far it reached (`reach_km`). |
| `select.petrolmate_fuel_type` | Which fuel the card shows. |
| `switch.petrolmate_<network>_card` | Include or exclude a network. With every switch off, all networks count. |
| `button.petrolmate_refresh` | Re-query now. |

### Example: notify when diesel is cheap nearby

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.petrolmate_cheapest_diesel
    below: 190
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Cheap diesel: {{ states('sensor.petrolmate_cheapest_diesel') }} c/L"
      message: "{{ state_attr('sensor.petrolmate_cheapest_diesel', 'station') }}, {{ state_attr('sensor.petrolmate_cheapest_diesel', 'distance_km') }} km"
      data:
        url: "{{ state_attr('sensor.petrolmate_cheapest_diesel', 'maps') }}"
```

## Good to know

- **Diesel in SA:** most South Australian stations list diesel only as *Premium Diesel*, so "Diesel" covers both the `DIESEL` and `PDIESEL` codes.
- **"since Thu"** on a tile is when the station last *changed* that price. Diesel often holds for days.
- **Prices** update every 6–12 hours from the government feeds, and the API caches for 2 minutes. Please keep the refresh interval sensible, since it's a free service.
- **Brand names** differ by state. If a station isn't being picked up, check its brand in the `top3` / `cheapest_any_brand` attributes and add it under **Configure → brands**.

## Credits and disclaimer

- Fuel prices are from [petrolmate.com.au](https://petrolmate.com.au) and the state government fuel pricing schemes.
- Map data is © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- Brand logos are trademarks of their owners. They aren't included in this repository; the card loads them from Wikimedia at runtime.

This project isn't affiliated with Petrolmate or any fuel retailer. Prices can be out of date, so always check the pump.

MIT licensed.
