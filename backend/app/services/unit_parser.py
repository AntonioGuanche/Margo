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
