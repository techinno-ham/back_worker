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
        """Establishes a connection pool to the database, retrying until successful."""
        while not self.connection_pool:
            try:
                # Try to establish the connection pool
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=5, maxconn=20, **self.db_params
                )
                logger.info("Database connection pool established")
            except OperationalError as e:
                # Log the error and retry after a delay
                logger.error(f"Database connection pool failed: {e}")
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
                
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
        """
        Inserts multiple records into the embeddings table in a single query.

        :param bot_id: The ID of the bot.
        :param records: A list of tuples where each tuple contains (content, metadata, embedding).
        :param embeddings: A list of embedded chunks.
        :param collection_id: The ID of the collection to which the records belong.
        """
        conn = self.get_connection()
        try:
            if not conn:
                raise Exception("Database connection is not established.")

            # Prepare the data for insertion
            values_list = []
            for doc, embedding in zip(records, embeddings):
                chunk_uuid = str(uuid.uuid4())
                content = doc.page_content
                metadata = doc.metadata
                values_list.append((collection_id, content, json.dumps(metadata), embedding, chunk_uuid))

            with conn.cursor() as cursor:
                
                #Sanitize for remving NUL character
                sanitized_values_list = [
                    tuple(v.replace('\x00', '') if isinstance(v, str) else v for v in row)
                    for row in values_list
                ]
                
                # Construct the SQL query dynamically using mogrify
                args_str = ','.join(
                    cursor.mogrify("(%s, %s, %s, %s, %s)", row).decode('utf-8')
                    for row in sanitized_values_list
                )
                
                insert_query = (
                    f"INSERT INTO langchain_pg_embedding (collection_id, document, cmetadata, embedding, uuid) "
                    f"VALUES {args_str} RETURNING uuid;"
                )

                # Execute the query
                cursor.execute(insert_query)
                inserted_ids = cursor.fetchall()

                # Update the bot status
                cursor.execute(
                    "UPDATE bots SET status = 'active' WHERE bot_id = %s;",
                    (bot_id,)
                )

                # Commit the transaction
                conn.commit()
                logger.info(f"Bulk inserted {len(values_list)} embedding records.")
                return [row[0] for row in inserted_ids]

        except Exception as e:
            # Rollback the transaction if there's an exception
            logger.error(f"Error bulk inserting embedding records: {e}")
            conn.rollback()
            raise e

        finally:
            # Release the connection back to the pool
            self.release_connection(conn)
# Singleton pattern to ensure only one instance of Database is created
database_instance = Database()
