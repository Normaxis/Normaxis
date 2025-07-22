from app import db
from sqlalchemy import text

with db.engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_section;"))
    conn.commit()
print("✅ Table _alembic_tmp_section supprimée.")
