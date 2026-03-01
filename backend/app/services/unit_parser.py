"""Parse packaging info from invoice line descriptions."""

import re

# Common Belgian brewery packaging patterns
PACKAGE_PATTERNS = [
    # "24/3" → 24 units of 33cl; "24/5" → 24 units of 50cl; "6/75" → 6 bottles of 75cl
    r'(\d+)\s*/\s*\d+',
    # "6x25cl", "12x33cl", "24x50cl"
    r'(\d+)\s*[xX×]\s*\d+',
    # "CASIER 24" or "CS24"
    r'(?:casier|caisse|cs|bac)\s*(\d+)',
]

# Descriptions that should NOT get units_per_package (bulk items)
BULK_KEYWORDS = ['fût', 'fut', 'bag in box', 'bib', 'vrac', 'citerne', 'cuve']


# Mapping for single-digit Belgian brewery notation
FRACTION_TO_CL: dict[int, int] = {
    2: 25,   # /2 → 25cl (quart)
    3: 33,   # /3 → 33cl (tiers)
    4: 40,   # /4 → 40cl
    5: 50,   # /5 → 50cl (demi)
    7: 75,   # /7 → 75cl
}


def parse_packaging_volume(description: str) -> dict | None:
    """Parse Belgian brewery packaging notation to extract count AND volume per unit.

    Returns dict with units, cl_per_unit, total_volume_liters, or None.

    Examples:
        "CHOUFFE BLONDE 24/3" → {units: 24, cl_per_unit: 33, total_volume_liters: 7.92}
        "PEPSI COLA 24/5"     → {units: 24, cl_per_unit: 50, total_volume_liters: 12.0}
        "6/75"                → {units: 6,  cl_per_unit: 75, total_volume_liters: 4.5}
        "SPA BARISART 28/4"   → {units: 28, cl_per_unit: 40, total_volume_liters: 11.2}
        "6x25cl"              → {units: 6,  cl_per_unit: 25, total_volume_liters: 1.5}
        "12x33cl"             → {units: 12, cl_per_unit: 33, total_volume_liters: 3.96}
        "STELLA ARTOIS 20L"   → None (keg — handled by parse_volume_liters)
        "FRITES SURGELEES"    → None (no packaging)
    """
    desc_lower = description.lower()

    # Skip bulk items
    if any(kw in desc_lower for kw in BULK_KEYWORDS):
        return None

    # Pattern 1: "24/3", "6/75", "28/4" — Belgian brewery notation
    match = re.search(r'(\d+)\s*/\s*(\d+)(?:\s|$|[^a-z0-9])', desc_lower)
    if match:
        units = int(match.group(1))
        second = int(match.group(2))

        if not (4 <= units <= 48):
            return None

        # Determine cl per unit
        if second <= 9:
            cl_per_unit = FRACTION_TO_CL.get(second)
            if cl_per_unit is None:
                return None
        elif 20 <= second <= 99:
            cl_per_unit = second  # Already in cl
        else:
            return None

        total_liters = round(units * cl_per_unit / 100, 4)
        return {
            "units": units,
            "cl_per_unit": cl_per_unit,
            "total_volume_liters": total_liters,
        }

    # Pattern 2: "6x25cl", "12x33cl", "24x50cl" — explicit format
    match = re.search(r'(\d+)\s*[xX×]\s*(\d+)\s*cl', desc_lower)
    if match:
        units = int(match.group(1))
        cl_per_unit = int(match.group(2))

        if not (4 <= units <= 48) or not (15 <= cl_per_unit <= 100):
            return None

        total_liters = round(units * cl_per_unit / 100, 4)
        return {
            "units": units,
            "cl_per_unit": cl_per_unit,
            "total_volume_liters": total_liters,
        }

    return None


def parse_units_per_package(description: str) -> int | None:
    """Extract units_per_package from a line description.

    Examples:
        "ORVAL 24/3" → 24
        "PEPSI COLA 24/5" → 24
        "LEFFE BLONDE 6% 24/3" → 24
        "1725 B&G PAYS D'OC 0.75L MERLOT" → None (wine bottle, no packaging info)
        "STELLA ARTOIS 20 L IFK" → None (keg)
        "BAG IN BOX 5 L" → None (bulk)
        "CAVA BRUT ESPATULA 0.75" → None (single bottle format)
        "SPA BARISART 28/4" → 28
    """
    desc_lower = description.lower()

    # Skip bulk items
    if any(kw in desc_lower for kw in BULK_KEYWORDS):
        return None

    for pattern in PACKAGE_PATTERNS:
        match = re.search(pattern, desc_lower)
        if match:
            value = int(match.group(1))
            # Sanity check: packaging is typically 4-48 units
            if 4 <= value <= 48:
                return value

    return None


# --- Volume-based portion calculation ---

def parse_volume_liters(description: str) -> float | None:
    """Extract total volume in liters from description.

    Examples:
        "STELLA ARTOIS 20 L IFK" → 20.0
        "BAG IN BOX 5 L" → 5.0
        "1725 B&G PAYS D'OC 0.75L MERLOT" → 0.75
        "CAVA BRUT ESPATULA 0.75" → 0.75
        "LEFFE BLONDE 6% 24/3" → None (handled by units_per_package)
    """
    desc_lower = description.lower()

    # Pattern: "20 L", "20L", "5 L", "0.75L", "0.75 L"
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*l(?:\s|$|[^a-z])', desc_lower)
    if match:
        value = float(match.group(1).replace(',', '.'))
        if 0.1 <= value <= 100:  # sanity check
            return value

    return None


def guess_serving_type(description: str) -> str | None:
    """Guess the serving type based on description keywords.

    Returns: 'beer', 'wine', 'spirit', or None
    """
    desc_lower = description.lower()

    beer_keywords = [
        'bière', 'biere', 'stella', 'leffe', 'chimay', 'orval',
        'westmalle', 'duvel', 'chouffe', 'rochefort', 'karmeliet',
        'hoegaarden', 'jupiler', 'maes', 'cristal', 'ipa', 'lager',
        'blonde', 'brune', 'triple', 'stout', 'pils', 'ifk', 'fût', 'fut',
        'godefroy', 'semois',
    ]

    wine_keywords = [
        'vin', 'wine', 'merlot', 'sauvignon', 'chardonnay', 'pinot',
        'cabernet', 'rosé', 'rose', 'cava', 'prosecco', 'champagne',
        'crémant', 'cremant', "pays d'oc", 'bordeaux', 'bourgogne',
        'côtes', 'cotes', 'bag in box', 'bib',
    ]

    spirit_keywords = [
        'whisky', 'whiskey', 'vodka', 'gin', 'rhum', 'rum',
        'cognac', 'porto', 'amaretto', 'pastis', 'ricard',
        'tequila', 'calvados', 'grappa', 'limoncello',
        'get 27', 'baileys', 'cointreau', 'grand marnier',
    ]

    if any(kw in desc_lower for kw in beer_keywords):
        return 'beer'
    if any(kw in desc_lower for kw in wine_keywords):
        return 'wine'
    if any(kw in desc_lower for kw in spirit_keywords):
        return 'spirit'
    return None


# Default serving sizes in cl
SERVING_SIZES: dict[str, float] = {
    'beer': 25,     # 25cl
    'wine': 12.5,   # 12.5cl (un verre)
    'spirit': 4,    # 4cl
}
