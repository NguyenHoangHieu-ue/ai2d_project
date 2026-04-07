from motor.motor_asyncio import AsyncIOMotorClient
import psycopg2
from neo4j import GraphDatabase
from app.core.config import settings

class DatabaseManager:
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.neo4j_driver = None
        self.pg_conn = None

    async def connect(self):
        # 1. MongoDB
        try:
            self.mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
            self.mongo_db = self.mongo_client[settings.MONGO_DB_NAME]
            # Test connection
            await self.mongo_client.server_info()
            print("Connected to MongoDB")
        except Exception as e:
            print(f"MongoDB Connection Error: {e}")

        # 2. Neo4j
        try:
            self.neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.neo4j_driver.verify_connectivity()
            print("Connected to Neo4j")
        except Exception as e:
            if self.neo4j_driver:
                try:
                    self.neo4j_driver.close()
                except Exception:
                    pass
            self.neo4j_driver = None
            print(f"Neo4j Connection Error: {e}")

        # 3. PostgreSQL
        try:
            self.pg_conn = psycopg2.connect(
                host=settings.POSTGRES_SERVER,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                dbname=settings.POSTGRES_DB
            )
            print("Connected to PostgreSQL")
        except Exception as e:
            print(f"Postgres Connection Error: {e}")

    def get_postgres_conn(self):
        # Reconnect if closed
        if self.pg_conn is None or self.pg_conn.closed:
            try:
                self.pg_conn = psycopg2.connect(
                    host=settings.POSTGRES_SERVER,
                    user=settings.POSTGRES_USER,
                    password=settings.POSTGRES_PASSWORD,
                    dbname=settings.POSTGRES_DB
                )
            except Exception as e:
                print(f"Reconnect Postgres Error: {e}")
                return None
        return self.pg_conn

    def put_postgres_conn(self, conn):
        pass

    def get_neo4j_session(self):
        if self.neo4j_driver:
            return self.neo4j_driver.session()
        return None

    async def close(self):
        if self.mongo_client: self.mongo_client.close()
        if self.neo4j_driver: self.neo4j_driver.close()
        if self.pg_conn: self.pg_conn.close()
        print("All database connections closed.")

db = DatabaseManager()