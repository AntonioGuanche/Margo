"""Utility functions for business logic."""

COCKTAIL_NAMES = {
    'mojito', 'cuba libre', 'sex on the beach', 'cosmopolitan', 'cosmo',
    'margarita', 'daiquiri', 'caipirinha', 'caipiroska', 'pina colada',
    'piña colada', 'tequila sunrise', 'long island', 'long island iced tea',
    'gin tonic', 'gin & tonic', 'gin-tonic', 'vodka tonic', 'vodka & tonic',
    'whisky coca', 'whisky-coca', 'jack cola', 'rhum coca', 'rhum-coca',
    'cuba', 'moscow mule', 'dark n stormy', 'dark and stormy',
    'spritz', 'aperol spritz', 'hugo', 'negroni', 'americano',
    'old fashioned', 'manhattan', 'martini dry', 'dry martini',
    'bloody mary', 'mimosa', 'bellini', 'kir', 'kir royal', 'kir royale',
    'irish coffee', 'espresso martini', 'b52', 'b-52',
    'ti punch', 'ti-punch', 'planteur', 'punch',
    'sangria', 'virgin mojito', 'virgin colada',
    'tom collins', 'whisky sour', 'whiskey sour', 'sour',
    'mai tai', 'blue lagoon', 'zombie', 'hurricane',
    'paloma', 'sidecar', 'french 75', 'gimlet',
    'pisco sour', 'amaretto sour', 'midori sour',
    'penicillin', 'mule', 'fizz', 'collins',
}

COCKTAIL_KEYWORDS = [
    'cocktail', 'mocktail', 'virgin', 'spritz', 'sour', 'mule',
    'fizz', 'collins', 'punch', 'sangria',
]


def is_cocktail(name: str) -> bool:
    """Detect if a dish name is a cocktail (= homemade, has sub-ingredients)."""
    name_lower = name.lower().strip()

    # Exact match
    if name_lower in COCKTAIL_NAMES:
        return True

    # Check if name contains a cocktail name (e.g., "Kir, Kir Royal" contains "kir")
    for cocktail in COCKTAIL_NAMES:
        if cocktail in name_lower:
            return True

    # Keyword match
    for kw in COCKTAIL_KEYWORDS:
        if kw in name_lower:
            return True

    return False


def guess_ingredient_category(name: str) -> str | None:
    """Guess ingredient category from its name (French / Belgian context)."""
    name_lower = name.lower()

    # Boissons
    boissons_kw = [
        "bière", "biere", "vin", "eau", "coca", "pepsi", "fanta", "jus",
        "café", "cafe", "thé", "limonade", "cidre", "whisky", "vodka",
        "gin", "rhum", "apéritif", "aperitif", "soda", "tonic", "schweppes",
        "stella", "leffe", "chimay", "orval", "westmalle", "duvel", "chouffe",
        "rochefort", "karmeliet", "hoegaarden", "jupiler", "maes", "cristal",
        "cava", "prosecco", "champagne", "cocktail", "spritz", "mojito",
        "martini", "porto", "cognac", "crémant", "bag in box", "sauvignon",
        "merlot", "chardonnay", "pinot", "cabernet", "rosé", "ipa",
        "blonde", "brune", "triple", "quadruple", "spa ", "perrier",
        "san pellegrino", "pellegrino", "cristaline", "orangina",
        "ice tea", "lipton", "godefroy", "semois", "pays d'oc",
        "barisart", "reine", "bru", "vittel", "evian", "contrex",
    ]
    if any(kw in name_lower for kw in boissons_kw):
        return "boissons"

    # Viandes & poissons
    viandes_kw = [
        "boeuf", "bœuf", "poulet", "porc", "veau", "agneau", "canard",
        "lapin", "saumon", "cabillaud", "thon", "crevette", "moule",
        "gambas", "lard", "bacon", "jambon", "saucisse", "merguez",
        "steak", "filet", "entrecôte", "viande", "poisson", "truite",
        "sole", "bar", "dorade", "homard", "langoustine", "boudin",
    ]
    if any(kw in name_lower for kw in viandes_kw):
        return "viandes & poissons"

    # Produits laitiers
    laitiers_kw = [
        "lait", "crème", "creme", "beurre", "fromage", "gruyère",
        "parmesan", "mozzarella", "yaourt", "mascarpone", "ricotta",
        "emmental", "comté", "camembert", "chèvre",
    ]
    if any(kw in name_lower for kw in laitiers_kw):
        return "produits laitiers"

    # Fruits & légumes
    fruits_legumes_kw = [
        "tomate", "oignon", "ail", "carotte", "pomme de terre", "salade",
        "laitue", "courgette", "poivron", "champignon", "épinard",
        "brocoli", "chou", "pomme", "citron", "orange", "fraise",
        "framboise", "banane", "avocat", "persil", "ciboulette",
        "basilic", "thym", "romarin", "menthe", "échalote",
    ]
    if any(kw in name_lower for kw in fruits_legumes_kw):
        return "fruits & légumes"

    # Épicerie & sec
    epicerie_kw = [
        "farine", "sucre", "sel", "poivre", "huile", "vinaigre",
        "pâtes", "pates", "riz", "pain", "moutarde", "ketchup",
        "mayo", "sauce", "conserve", "olive", "épice", "curry",
        "paprika", "cumin", "noix", "amande", "chocolat", "cacao",
        "levure", "gélatine", "chapelure", "semoule",
    ]
    if any(kw in name_lower for kw in epicerie_kw):
        return "épicerie & sec"

    # Surgelés
    surgeles_kw = ["surgelé", "surgele", "congelé", "congele", "frozen"]
    if any(kw in name_lower for kw in surgeles_kw):
        return "surgelés"

    return None
