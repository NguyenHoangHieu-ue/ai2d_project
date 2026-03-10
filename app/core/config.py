import os
from dotenv import load_dotenv

load_dotenv()


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


settings = Settings()