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
