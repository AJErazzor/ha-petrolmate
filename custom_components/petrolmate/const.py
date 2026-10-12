"""Constants for the Petrolmate integration."""

from __future__ import annotations

DOMAIN = "petrolmate"

API_URL = "https://petrolmate.com.au/api/v1/stations/area"
API_LIMIT = 50  # API maximum; the nearest 50 stations are returned
API_TIMEOUT = 20

CONF_LOCATION_ENTITY = "location_entity"
CONF_RADIUS = "radius"
CONF_FUELS = "fuels"
CONF_NETWORKS = "networks"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MOVE_DISTANCE = "move_distance"
CONF_BRANDS_PREFIX = "brands_"
CONF_STATES = "states"
CONF_DISCOUNTS = "discounts"

DEFAULT_NAME = "Petrolmate"
DEFAULT_LOCATION_ENTITY = "zone.home"
DEFAULT_RADIUS = 20  # km
DEFAULT_FUELS = ["DIESEL", "ULP"]
DEFAULT_NETWORKS = ["bp", "shell", "ampol"]
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_MOVE_DISTANCE = 500  # metres moved before re-querying

# Fuel selections offered to the user → API fuel codes.
# Most SA stations list diesel only as PDIESEL, so "Diesel" covers both codes.
FUELS: dict[str, dict] = {
    "DIESEL": {"name": "Diesel", "codes": ["DIESEL", "PDIESEL"]},
    "ULP": {"name": "Unleaded 91", "codes": ["ULP"]},
    "E10": {"name": "E10", "codes": ["E10"]},
    "PULP95": {"name": "Premium 95", "codes": ["PULP95"]},
    "PULP98": {"name": "Premium 98", "codes": ["PULP98"]},
    "LPG": {"name": "LPG", "codes": ["LPG"]},
}

# The API's `state` codes, in the order offered in setup.
STATES: dict[str, str] = {
    "SA": "South Australia", "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland",
    "WA": "Western Australia", "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "Australian Capital Territory",
}

# Station brands commonly seen in each state's price feed — the starting pick-list for "where each fuel brand
# is sold" and for discounts. Not exhaustive: brands seen in the latest search are added, and any name can be typed.
STATE_BRANDS: dict[str, list[str]] = {
    "SA": ["OTR", "X Convenience", "BP", "Shell", "Ampol", "EG Ampol", "Ampol Foodary", "Caltex", "Mobil", "United",
           "Liberty", "Metro Petroleum", "AM/PM", "Perrys", "Solo", "Pearl Energy", "Speedway", "Costco", "Independent"],
    "NSW": ["7-Eleven", "Ampol", "EG Ampol", "Ampol Foodary", "U-GO", "BP", "Caltex", "Shell", "Reddy Express",
            "Coles Express", "Metro Petroleum", "United", "Speedway", "Mobil", "Liberty", "Costco", "Budget", "Enhance",
            "Westside", "Lowes", "Astron", "Inland Petroleum", "Puma Energy", "Independent"],
    "VIC": ["7-Eleven", "Ampol", "EG Ampol", "Ampol Foodary", "U-GO", "BP", "Caltex", "Shell", "Reddy Express",
            "Coles Express", "United", "Liberty", "Speedway", "Mobil", "Metro Petroleum", "Apco", "Costco", "Independent"],
    "QLD": ["7-Eleven", "Puma Energy", "Ampol", "EG Ampol", "Ampol Foodary", "U-GO", "BP", "Caltex", "Shell",
            "Reddy Express", "Coles Express", "United", "Liberty", "Freedom Fuels", "Mobil", "Metro Petroleum",
            "Pearl Energy", "Lowes", "Costco", "Independent"],
    "WA": ["Vibe", "Better Choice", "Puma Energy", "Caltex", "Ampol", "BP", "Shell", "Reddy Express", "United",
           "7-Eleven", "Liberty", "Gull", "Peak", "X Convenience", "Wesco", "Costco", "Independent"],
    "TAS": ["Bennett's Petroleum", "Bonney Energy", "Ampol", "BP", "Caltex", "Shell", "United", "Puma Energy",
            "Astron", "Liberty", "Independent"],
    "NT": ["United", "Puma Energy", "BP", "Shell", "Ampol", "Caltex", "Liberty", "Independent"],
    "ACT": ["7-Eleven", "Ampol", "Ampol Foodary", "BP", "Caltex", "Shell", "Reddy Express", "Coles Express",
            "Mobil", "Costco", "Independent"],
}

# Fuel brands → the station brands they're sold under (as the API reports them, matched case-insensitively).
# Internally still called "networks" (config keys, entity unique ids) so existing installs keep working.
# Defaults are editable per install in the integration options. Logos are hotlinked from Wikimedia at
# runtime by the card (trademarks aren't shipped); networks without one fall back to their colour.
NETWORKS: dict[str, dict] = {
    "bp": {"name": "BP", "color": "#009900", "brands": ["BP", "X Convenience"], "logo": "https://upload.wikimedia.org/wikipedia/en/d/d2/BP_Helios_logo.svg"},
    "shell": {"name": "Shell", "color": "#e0b400", "brands": ["Shell", "OTR", "Reddy Express", "Coles Express"], "logo": "https://upload.wikimedia.org/wikipedia/en/e/e8/Shell_logo.svg"},
    "ampol": {"name": "Ampol", "color": "#e1251b", "brands": ["Ampol", "EG Ampol", "Ampol Foodary", "U-GO"], "logo": "https://upload.wikimedia.org/wikipedia/en/4/4e/Ampol_Logo_May_2020.svg"},
    "caltex": {"name": "Caltex", "color": "#00a1de", "brands": ["Caltex", "Star Mart", "Caltex Woolworths"], "logo": "https://upload.wikimedia.org/wikipedia/commons/f/f6/Caltex_brand_logo.svg"},
    "7eleven": {"name": "7-Eleven", "color": "#ee7d00", "brands": ["7-Eleven"], "logo": "https://upload.wikimedia.org/wikipedia/commons/e/e0/7-Eleven_logo_2021.svg"},
    "mobil": {"name": "Mobil", "color": "#d6001c", "brands": ["Mobil"], "logo": "https://upload.wikimedia.org/wikipedia/commons/3/3d/Mobil_logo.svg"},
    "united": {"name": "United", "color": "#003da5", "brands": ["United"], "logo": "https://upload.wikimedia.org/wikipedia/en/8/88/United-logo-300.png"},
    "metro": {"name": "Metro", "color": "#5b2c86", "brands": ["Metro Petroleum", "Metro"]},
    "puma": {"name": "Puma", "color": "#c8102e", "brands": ["Puma Energy", "Puma"], "logo": "https://upload.wikimedia.org/wikipedia/commons/b/ba/Puma_Energy_logo.svg"},
    "liberty": {"name": "Liberty", "color": "#1d4f91", "brands": ["Liberty"], "logo": "https://upload.wikimedia.org/wikipedia/en/1/13/Liberty_Oil_logo.png"},
    "costco": {"name": "Costco", "color": "#005daa", "brands": ["Costco"], "logo": "https://upload.wikimedia.org/wikipedia/commons/5/59/Costco_Wholesale_logo_2010-10-26.svg"},
}

ATTRIBUTION = "Fuel prices from petrolmate.com.au (state government fuel price feeds)"
MANUFACTURER = "AJErazzor"
MODEL = "Fuel prices · petrolmate.com.au data"
