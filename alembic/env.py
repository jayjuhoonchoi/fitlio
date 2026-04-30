import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Fitlio 모델 인식 ──────────────────────────────────────────
# app/ 폴더를 Python path에 추가 (모델 import 위해)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Base  # noqa: E402
import app.models  # noqa: E402, F401 — 모든 모델 등록 보장

# ── Alembic 기본 설정 ─────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata  # ← 핵심: None → Base.metadata

# ── DB URL: 환경변수에서 읽기 (하드코딩 금지) ─────────────────
def get_url():
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://fitlio:fitlio@localhost:5432/fitlio"  # 로컬 fallback
    )

# ── Offline 모드 (DB 없이 SQL 파일만 생성) ───────────────────
def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# ── Online 모드 (실제 DB 연결해서 마이그레이션) ──────────────
def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()  # ini 파일 URL 무시, 환경변수 우선
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()