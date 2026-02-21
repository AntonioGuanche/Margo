"""Tests for invoice line → ingredient matching service."""

from app.models.ingredient import Ingredient
from app.models.ingredient_alias import IngredientAlias
from app.services.matching import match_invoice_lines
from app.services.parser_xml import InvoiceLine


async def test_match_exact_name(db_session, restaurant):
    """Ingredient 'Boeuf haché' exists → match exact."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=12.0,
    )
    db_session.add(ingredient)
    await db_session.flush()

    lines = [InvoiceLine(description="Boeuf haché", quantity=5.0)]
    results = await match_invoice_lines(db_session, restaurant.id, lines)

    assert len(results) == 1
    assert results[0].matched_ingredient_id == ingredient.id
    assert results[0].matched_ingredient_name == "Boeuf haché"
    assert results[0].confidence == "exact"


async def test_match_exact_case_insensitive(db_session, restaurant):
    """Matching should be case-insensitive."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=12.0,
    )
    db_session.add(ingredient)
    await db_session.flush()

    lines = [InvoiceLine(description="BOEUF HACHÉ", quantity=5.0)]
    results = await match_invoice_lines(db_session, restaurant.id, lines)

    assert len(results) == 1
    assert results[0].confidence == "exact"
    assert results[0].matched_ingredient_id == ingredient.id


async def test_match_alias(db_session, restaurant):
    """Alias 'BOEUF HACHE 1ERE' → match via alias."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=12.0,
    )
    db_session.add(ingredient)
    await db_session.flush()

    alias = IngredientAlias(
        restaurant_id=restaurant.id,
        alias_text="BOEUF HACHE 1ERE",
        ingredient_id=ingredient.id,
    )
    db_session.add(alias)
    await db_session.flush()

    lines = [InvoiceLine(description="BOEUF HACHE 1ERE", quantity=5.0)]
    results = await match_invoice_lines(db_session, restaurant.id, lines)

    assert len(results) == 1
    assert results[0].matched_ingredient_id == ingredient.id
    assert results[0].confidence == "alias"


async def test_match_none(db_session, restaurant):
    """No similar ingredient exists → confidence='none'."""
    # Add an ingredient that's totally unrelated
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Crème fraîche",
        unit="l",
        current_price=3.0,
    )
    db_session.add(ingredient)
    await db_session.flush()

    lines = [InvoiceLine(description="Câpres de Pantelleria", quantity=1.0)]
    results = await match_invoice_lines(db_session, restaurant.id, lines)

    assert len(results) == 1
    assert results[0].confidence == "none"
    assert results[0].matched_ingredient_id is None
    # Should have suggestions (top ingredients)
    assert len(results[0].suggestions) >= 1


async def test_match_multiple_lines(db_session, restaurant):
    """Match multiple invoice lines in one call."""
    ing1 = Ingredient(restaurant_id=restaurant.id, name="Boeuf haché", unit="kg", current_price=12.0)
    ing2 = Ingredient(restaurant_id=restaurant.id, name="Lard fumé", unit="kg", current_price=7.5)
    db_session.add_all([ing1, ing2])
    await db_session.flush()

    lines = [
        InvoiceLine(description="Boeuf haché", quantity=5.0),
        InvoiceLine(description="Lard fumé", quantity=2.0),
        InvoiceLine(description="Unknown item", quantity=1.0),
    ]
    results = await match_invoice_lines(db_session, restaurant.id, lines)

    assert len(results) == 3
    assert results[0].confidence == "exact"
    assert results[1].confidence == "exact"
    assert results[2].confidence == "none"
