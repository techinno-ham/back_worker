import psycopg2
import json
import uuid
import os
from dotenv import load_dotenv
import time
from psycopg2 import OperationalError
from psycopg2 import pool
import logging

# Load environment variables from .env file
load_dotenv(override=True)

# Define database connection parameters
db_params = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection_pool = None
        self.db_params = db_params
        self.connect()

    def connect(self):
        """Establishes a connection pool to the database."""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=5, maxconn=20, **self.db_params
            )
            logger.info("Database connection pool established")
        except OperationalError as e:
            logger.error(f"Database connection pool failed: {e}")
            raise Exception("Could not establish connection pool.")

    def get_connection(self):
        """Get a connection from the pool."""
        if not self.connection_pool:
            self.connect()  # Ensure pool is created if not already
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        """Release a connection back to the pool."""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def disconnect(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed.")

    def execute_query(self, query):
        """Executes an SQL query on the database."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                conn.commit()
                logger.info(f"Executed query: {query}")
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            conn.rollback()
        finally:
            self.release_connection(conn)

    def fetch_data(self, query):
        """Fetches data from the database using the provided query."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                logger.info(f"Fetched data: {result}")
                return result
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
        finally:
            self.release_connection(conn)

    def return_collection_uuid(self, bot_id):
        """Fetches and returns the collection UUID for a given bot_id."""
        query = """
        SELECT uuid
        FROM langchain_pg_collection
        WHERE name = %s;
        """
        try:
            result = self.fetch_data(query, (bot_id,))
            if result:
                return result[0][0]
            else:
                raise Exception(f"No collection found for bot_id {bot_id}")
        except Exception as e:
            logger.error(f"Error retrieving collection for bot_id {bot_id}: {e}")
            raise e

    def create_or_return_collection_uuid(self, bot_id):
        """Creates a new collection or returns existing collection UUID."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM langchain_pg_collection WHERE name = %s;", (bot_id,))
                collection_uuid = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO langchain_pg_collection (name, cmetadata, uuid) VALUES (%s, %s, %s) RETURNING uuid;",
                    (bot_id, None, collection_uuid)
                )
                collection_uuid = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"Collection UUID for {bot_id}: {collection_uuid}")
                return collection_uuid
        except Exception as e:
            logger.error(f"Error creating or returning collection for bot_id {bot_id}: {e}")
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def insert_embedding_record(self, bot_id, content, metadata, embedding, collection_id):
        """Inserts a new record into the embeddings table."""
        conn = self.get_connection()
        try:
            chunk_uuid = str(uuid.uuid4())
            query = """
            INSERT INTO langchain_pg_embedding (collection_id, document, cmetadata, embedding, uuid)
            VALUES (%s, %s, %s, %s, %s) RETURNING uuid;
            """
            with conn.cursor() as cursor:
                cursor.execute(query, (collection_id, content, json.dumps(metadata), embedding, chunk_uuid))
                inserted_id = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"Inserted embedding record with UUID: {inserted_id}")
                return inserted_id
        except Exception as e:
            logger.error(f"Error inserting embedding record: {e}")
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def bulk_insert_embedding_record(self, bot_id, records, embeddings, collection_id):
        """Inserts multiple records into the embeddings table in a single query."""
        conn = self.get_connection()
        try:
            values_list = [
                (collection_id, doc.page_content, json.dumps(doc.metadata), embedding, str(uuid.uuid4()))
                for doc, embedding in zip(records, embeddings)
            ]

            insert_query = """
            INSERT INTO langchain_pg_embedding (collection_id, document, cmetadata, embedding, uuid)
            VALUES %s RETURNING uuid;
            """
            with conn.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor, insert_query, values_list, template=None, page_size=100
                )
                conn.commit()
                logger.info(f"Bulk inserted {len(values_list)} embedding records")
        except Exception as e:
            logger.error(f"Error bulk inserting embedding records: {e}")
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

# Singleton pattern to ensure only one instance of Database is created
database_instance = Database()
