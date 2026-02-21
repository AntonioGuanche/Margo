"""
Performance checker — verify DB indexes and query patterns.

Run manually: cd backend && python -m scripts.check_performance
"""

import asyncio
import logging

from sqlalchemy import text

from app.config import settings
from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def check_indexes() -> None:
    """List all indexes and verify foreign keys have indexes."""
    async with engine.begin() as conn:
        # Get all indexes
        result = await conn.execute(text("""
            SELECT
                t.relname AS table_name,
                i.relname AS index_name,
                a.attname AS column_name
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relkind = 'r'
            AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY t.relname, i.relname
        """))
        rows = result.fetchall()

        logger.info("=" * 60)
        logger.info("EXISTING INDEXES")
        logger.info("=" * 60)
        current_table = ""
        for row in rows:
            if row[0] != current_table:
                current_table = row[0]
                logger.info(f"\n  {current_table}:")
            logger.info(f"    - {row[1]} ({row[2]})")

        # Check FK without indexes
        result = await conn.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """))
        fks = result.fetchall()

        logger.info("\n" + "=" * 60)
        logger.info("FOREIGN KEY INDEX CHECK")
        logger.info("=" * 60)

        indexed_columns = {(row[0], row[2]) for row in rows}
        for fk in fks:
            has_index = (fk[0], fk[1]) in indexed_columns
            status = "✅" if has_index else "❌ MISSING INDEX"
            logger.info(f"  {fk[0]}.{fk[1]} → {fk[2]}: {status}")


async def check_table_sizes() -> None:
    """Show table row counts."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT relname, n_live_tup
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC
        """))
        rows = result.fetchall()

        logger.info("\n" + "=" * 60)
        logger.info("TABLE ROW COUNTS")
        logger.info("=" * 60)
        for row in rows:
            logger.info(f"  {row[0]}: {row[1]} rows")


async def main() -> None:
    logger.info(f"Database: {settings.database_url[:40]}...")
    await check_indexes()
    await check_table_sizes()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
