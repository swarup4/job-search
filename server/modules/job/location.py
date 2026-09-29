"""Country and cities out of a board's free-text `location`, with no model involved.

Boards write the same place dozens of ways — `Bangalore,IND, India`, `IN - Bengaluru,
India`, `1401-GIPL: Prestige Technology Park IV, Bangalore, India`. What is read here is
only what the text names: an unknown country is None and an unreadable place adds no
city, because a filter that trusts a guessed country hides real jobs.
"""

import re

import pycountry

# ISO 3166 names every country; these are the spellings boards use that it does not.
EXTRA_ALIASES: dict[str, str] = {
    "usa": "US",
    "united states of america": "US",
    "uk": "GB",
    "great britain": "GB",
    "britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "uae": "AE",
    "czech republic": "CZ",
    "turkey": "TR",
    "russia": "RU",
    "holland": "NL",
    "the netherlands": "NL",
    "deutschland": "DE",
    "korea": "KR",
    "ivory coast": "CI",
    "macedonia": "MK",
    "palestine": "PS",
    "vatican": "VA",
    "hong kong sar": "HK",
}

# Shown instead of ISO's formal name.
DISPLAY: dict[str, str] = {"RU": "Russia"}

# Also US states ("Atlanta, Georgia", "New Jersey"), so never read as a country: an
# unknown country is null, a wrong one hides the job.
AMBIGUOUS = {"georgia", "jersey"}

# Codes count only as a whole comma part in capitals, where office codes cannot pass
# for one. These four also count anywhere, because the stored data spells them so.
LOOSE_CODES = {"IN": "IN", "IND": "IN", "US": "US", "UK": "GB"}


def _display(alpha_2: str) -> str:
    country = pycountry.countries.get(alpha_2=alpha_2)
    return DISPLAY.get(alpha_2) or getattr(country, "common_name", None) or country.name


def _build() -> tuple[dict[str, str], dict[str, str]]:
    names: dict[str, str] = {}
    codes: dict[str, str] = {code: _display(alpha_2) for code, alpha_2 in LOOSE_CODES.items()}
    for country in pycountry.countries:
        display = _display(country.alpha_2)
        for name in (country.name, getattr(country, "official_name", None),
                     getattr(country, "common_name", None)):  # fmt: skip
            if name:
                names[name.lower()] = display
        codes[country.alpha_2] = codes[country.alpha_3] = display
    for alias, alpha_2 in EXTRA_ALIASES.items():
        names[alias] = _display(alpha_2)
    for alias in AMBIGUOUS:
        names.pop(alias, None)
    return names, codes


COUNTRY_NAMES, COUNTRY_CODES = _build()

# Indian postings are where the office codes and building names are, so these are
# found anywhere in a place. Longest first, so "Greater Noida" is not also "Noida".
CITIES: dict[str, tuple[str, ...]] = {
    "Bengaluru": ("bengaluru", "bangalore"),
    "Hyderabad": ("hyderabad",),
    "Pune": ("pune",),
    "Mumbai": ("mumbai", "bombay"),
    "Chennai": ("chennai", "madras"),
    "Greater Noida": ("greater noida",),
    "Noida": ("noida",),
    "Gurugram": ("gurugram", "gurgaon"),
    "New Delhi": ("new delhi",),
    "Delhi": ("delhi",),
    "Kolkata": ("kolkata", "calcutta"),
    "Coimbatore": ("coimbatore",),
    "Nagpur": ("nagpur",),
    "Jaipur": ("jaipur",),
    "Bhubaneswar": ("bhubaneswar",),
    "Indore": ("indore",),
    "Ahmedabad": ("ahmedabad",),
    "Kochi": ("kochi", "cochin"),
    "Thiruvananthapuram": ("thiruvananthapuram", "trivandrum"),
    "Chandigarh": ("chandigarh",),
    "Mysuru": ("mysuru", "mysore"),
    "Vadodara": ("vadodara", "baroda"),
    "Visakhapatnam": ("visakhapatnam", "vizag"),
}

# A first comma part that is one of these is a region, not a city.
REGIONS = {
    "karnataka", "karnātaka", "tamil nadu", "maharashtra", "telangana", "haryana",
    "uttar pradesh", "kerala", "gujarat", "west bengal", "andhra pradesh", "delhi ncr",
    "remote", "virtual", "anywhere",
}  # fmt: skip

_CITY_ALIASES = sorted(
    ((alias, name) for name, aliases in CITIES.items() for alias in aliases),
    key=lambda pair: -len(pair[0]),
)
_PLAIN_NAME = re.compile(r"[A-Za-z][A-Za-z .'-]*")


def canonical_country(value: str | None) -> str | None:
    """A board's own country field, in the spelling the rest of the data uses."""
    if not value or not value.strip():
        return None
    return _country_of(value.strip()) or value.strip()


def parse_location(location: str) -> tuple[str | None, list[str]]:
    """(country, cities). The country is the posting's primary one — the last named."""
    places = [place.strip() for place in location.split(";") if place.strip()]
    tail = location.rsplit(",", 1)[-1].strip()
    country = _country_of(tail) or _first_country(location)

    cities: list[str] = []
    for place in places:
        for city in _cities_in(place):
            if city not in cities:
                cities.append(city)
    return country, cities


def _country_of(value: str) -> str | None:
    return COUNTRY_CODES.get(value) or COUNTRY_NAMES.get(value.lower())


# Longest first, so "Papua New Guinea" is found before "Guinea".
_ANYWHERE = re.compile(
    r"(?<![a-z])("
    + "|".join(re.escape(name) for name in sorted(COUNTRY_NAMES, key=len, reverse=True))
    + r")(?![a-z])"
)
_ANYWHERE_CODE = re.compile(r"(?<![A-Za-z])(" + "|".join(LOOSE_CODES) + r")(?![A-Za-z])")


def _first_country(text: str) -> str | None:
    """A country named anywhere, for the spellings with none at the end."""
    if found := _ANYWHERE.search(text.lower()):
        return COUNTRY_NAMES[found.group(1)]
    if found := _ANYWHERE_CODE.search(text):
        return COUNTRY_CODES[found.group(1)]
    return None


def _cities_in(place: str) -> list[str]:
    lowered = place.lower()
    found: list[str] = []
    for alias, name in _CITY_ALIASES:
        pattern = rf"(?<![a-z]){re.escape(alias)}(?![a-z])"
        if re.search(pattern, lowered):
            lowered = re.sub(pattern, " ", lowered)
            if name not in found:
                found.append(name)
    if found:
        return found

    # Outside the known list, only a place written plainly as "City, Region[, Country]"
    # gives a city — codes, digits and parentheses mean the first part is not one, and
    # a lone name with no region after it is as often a building ("RMZ TITANIUM").
    first, comma, _ = place.partition(",")
    first = first.strip()
    if (
        comma
        and _PLAIN_NAME.fullmatch(first)
        and first.lower() not in REGIONS
        and _country_of(first) is None
    ):
        return [first]
    return []


if __name__ == "__main__":
    for sample in [
        "Bangalore,IND, India",
        "1401-G-India: DLF Commercial Building 3, Phase V, Gurugram",
        "Bengaluru, Karnātaka, India; Bucharest, Ilfov, Romania; Chennai, Tamil Nadu, India",
        "Tamil Nadu, India",
    ]:
        print(f"{sample!r:>90} -> {parse_location(sample)}")
