"""Invoice line → ingredient matching service.

Order: alias exact → name exact (case-insensitive) → fuzzy (pg_trgm) → no match.
"""

from dataclasses import dataclass, field

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingredient import Ingredient
from app.models.ingredient_alias import IngredientAlias
from app.services.parser_xml import InvoiceLine


@dataclass
class MatchResult:
    """Result of matching an invoice line to an ingredient."""

    invoice_line: InvoiceLine
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None
    confidence: str = "none"  # "exact", "alias", "fuzzy", "none"
    suggestions: list[dict] = field(default_factory=list)  # [{id, name, score}]


async def _check_pg_trgm(db: AsyncSession) -> bool:
    """Check if pg_trgm extension is available."""
    try:
        result = await db.execute(text(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
        ))
        return result.scalar() is not None
    except Exception:
        return False


async def match_invoice_lines(
    db: AsyncSession,
    restaurant_id: int,
    lines: list[InvoiceLine],
) -> list[MatchResult]:
    """Match each invoice line to the best ingredient.

    Order:
    1. Alias exact match (case-insensitive) from IngredientAlias
    2. Name exact match (case-insensitive) from Ingredient.name
    3. Fuzzy match via pg_trgm similarity > 0.3
    4. No match → return top 5 ingredients as suggestions
    """
    results: list[MatchResult] = []
    has_trgm = await _check_pg_trgm(db)

    for line in lines:
        description = line.description.strip()
        match = await _match_single_line(db, restaurant_id, description, has_trgm)
        match.invoice_line = line
        results.append(match)

    return results


async def _match_single_line(
    db: AsyncSession,
    restaurant_id: int,
    description: str,
    has_trgm: bool,
) -> MatchResult:
    """Try to match a single invoice line description to an ingredient."""

    # 1. Alias exact match (case-insensitive)
    alias_result = await db.execute(
        select(IngredientAlias)
        .where(
            IngredientAlias.restaurant_id == restaurant_id,
            func.lower(IngredientAlias.alias_text) == description.lower(),
        )
    )
    alias = alias_result.scalar_one_or_none()
    if alias:
        # Get the ingredient name
        ingredient_result = await db.execute(
            select(Ingredient).where(Ingredient.id == alias.ingredient_id)
        )
        ingredient = ingredient_result.scalar_one_or_none()
        if ingredient:
            return MatchResult(
                invoice_line=InvoiceLine(description=description),
                matched_ingredient_id=ingredient.id,
                matched_ingredient_name=ingredient.name,
                confidence="alias",
            )

    # 2. Name exact match (case-insensitive)
    exact_result = await db.execute(
        select(Ingredient)
        .where(
            Ingredient.restaurant_id == restaurant_id,
            func.lower(Ingredient.name) == description.lower(),
        )
    )
    exact = exact_result.scalar_one_or_none()
    if exact:
        return MatchResult(
            invoice_line=InvoiceLine(description=description),
            matched_ingredient_id=exact.id,
            matched_ingredient_name=exact.name,
            confidence="exact",
        )

    # 3. Fuzzy match with pg_trgm
    if has_trgm:
        fuzzy_result = await db.execute(
            text("""
                SELECT id, name, similarity(name, :desc) as score
                FROM ingredients
                WHERE restaurant_id = :rid AND similarity(name, :desc) > 0.3
                ORDER BY score DESC
                LIMIT 3
            """),
            {"desc": description, "rid": restaurant_id},
        )
        fuzzy_rows = fuzzy_result.fetchall()

        if fuzzy_rows:
            best = fuzzy_rows[0]
            suggestions = [
                {"id": row[0], "name": row[1], "score": round(float(row[2]), 3)}
                for row in fuzzy_rows
            ]
            return MatchResult(
                invoice_line=InvoiceLine(description=description),
                matched_ingredient_id=best[0],
                matched_ingredient_name=best[1],
                confidence="fuzzy",
                suggestions=suggestions,
            )

    # 4. No match — return top 5 ingredients as suggestions
    top_result = await db.execute(
        select(Ingredient.id, Ingredient.name)
        .where(Ingredient.restaurant_id == restaurant_id)
        .order_by(Ingredient.name)
        .limit(5)
    )
    top_rows = top_result.fetchall()
    suggestions = [
        {"id": row[0], "name": row[1], "score": 0.0}
        for row in top_rows
    ]

    return MatchResult(
        invoice_line=InvoiceLine(description=description),
        confidence="none",
        suggestions=suggestions,
    )


async def save_alias(
    db: AsyncSession,
    restaurant_id: int,
    alias_text: str,
    ingredient_id: int,
) -> None:
    """Save an alias mapping for future auto-matching.

    Skips if alias already exists for this restaurant.
    """
    # Check if alias already exists
    existing = await db.execute(
        select(IngredientAlias)
        .where(
            IngredientAlias.restaurant_id == restaurant_id,
            func.lower(IngredientAlias.alias_text) == alias_text.lower(),
        )
    )
    if existing.scalar_one_or_none():
        return

    alias = IngredientAlias(
        restaurant_id=restaurant_id,
        alias_text=alias_text,
        ingredient_id=ingredient_id,
    )
    db.add(alias)
    await db.flush()
