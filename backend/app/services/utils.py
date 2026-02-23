"""Utility functions for business logic."""


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
        "san pellegrino", "pellegrino", "cristaline",
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
