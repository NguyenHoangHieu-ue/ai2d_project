import os
import json
from dotenv import load_dotenv

load_dotenv()


def _normalize_origin(origin: str) -> str:
    cleaned = origin.strip().strip('"').strip("'")
    return cleaned[:-1] if cleaned.endswith("/") else cleaned


def _parse_cors_allow_origins(raw_value: str) -> list[str]:
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return []

    parsed_values: list[str]
    if raw_value.startswith("[") and raw_value.endswith("]"):
        try:
            loaded = json.loads(raw_value)
            if isinstance(loaded, list):
                parsed_values = [str(item) for item in loaded]
            else:
                parsed_values = [raw_value]
        except json.JSONDecodeError:
            parsed_values = raw_value.split(",")
    else:
        parsed_values = raw_value.split(",")

    normalized: list[str] = []
    for origin in parsed_values:
        cleaned = _normalize_origin(origin)
        if cleaned:
            normalized.append(cleaned)
    return normalized


class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # Database
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ai2d_knowledge_graph")

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

    POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "ai2d_db")

    # Storage
    R2_BASE_URL = os.getenv("R2_BASE_URL", "")

    # CORS
    CORS_ALLOW_ORIGINS = _parse_cors_allow_origins(
        os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )
    CORS_ALLOW_ORIGIN_REGEX = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "").strip() or None


settings = Settings()