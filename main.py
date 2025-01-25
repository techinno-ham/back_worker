from dotenv import load_dotenv

import logging
from confluent_kafka import Consumer
from db import database_instance
from embed import create_document_embedding
import asyncio
import os
import json
from modules.qa_processor import handle_qa_datasource
from modules.s3_processor import handle_files_from_s3
from modules.link_processor import handle_urls_datasource
from modules.text_processor import handle_text_datasource
import pika

import time
from confluent_kafka import Consumer, KafkaException

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

from logging_config import setup_logging

# Load the logging configuration
logger, queue_listener = setup_logging()

load_dotenv(override=True)

rabbitmq_conf = {
    'host': os.getenv("RABBITMQ_HOST"),
    'queue': os.getenv("RABBITMQ_QUEUE"),
    'username': os.getenv("RABBITMQ_USERNAME"),
    'password': os.getenv("RABBITMQ_PASSWORD"),
    'virtual_host': os.getenv("RABBITMQ_VHOST")
}

async def handle_qa_update(bot_id,datasource_id,datasources):
    tasks = []

    log_metadata = {
        'bot_id': bot_id,
        'datasource_id': datasource_id,
    }

    if 'qa' in datasources:
        tasks.append(handle_qa_datasource(datasources['qa'] , log_metadata))

    all_chunks = await asyncio.gather(*tasks)

    flattened_list = [item for sublist in all_chunks for item in sublist]

    return flattened_list
    
    
async def handle_qa_job(msg_obj):
    try:
        
        bot_id = msg_obj.get('botId', None)
        datasource_id = msg_obj.get('datasourceId', None)
        datasources = msg_obj.get('datasources', None)
        
        log_metadata = {"bot_id":bot_id,"datasource_id":datasource_id }
        
        all_chunks = await handle_qa_update(bot_id,datasource_id, datasources)

        # Check if all_chunks has any content
        if all_chunks:  # More Pythonic way to check if list is not empty
            collection_id = database_instance.return_collection_uuid(bot_id)
            logger.info("Collection ID created: %s", collection_id)

            embedded_chunks = create_document_embedding(all_chunks)

            database_instance.bulk_insert_embedding_record(
                bot_id=bot_id,
                records=all_chunks,
                embeddings=embedded_chunks,
                collection_id=collection_id
            )
            
            

            logger.info("Successfully processed and stored data for bot: %s s", bot_id  ,extra={"metadata": log_metadata})
        else:
            logger.warning("No chunks were generated for bot: %s", bot_id ,extra={"metadata": log_metadata})

    except Exception as e:
        logger.error("Error handling the job for bot: %s ", bot_id ,extra={"metadata": log_metadata}, exc_info=True)
        raise e


async def aggregate_results(bot_id,datasource_id,datasources):
    tasks = []

    log_metadata = {
        'bot_id': bot_id,
        'datasource_id': datasource_id,
    }

    if 'text' in datasources:
        tasks.append(handle_text_datasource(datasources['text'] , log_metadata))

    if 'qa' in datasources:
        tasks.append(handle_qa_datasource(datasources['qa'] , log_metadata))

    if 'urls' in datasources:
        tasks.append(handle_urls_datasource(datasources['urls'] , log_metadata))

    if 'files' in datasources:
        tasks.append(handle_files_from_s3(datasources['files'] , log_metadata))

    all_chunks = await asyncio.gather(*tasks)

    flattened_list = [item for sublist in all_chunks for item in sublist]

    return flattened_list


async def handle_incoming_job_events(msg_obj):
    try:
        bot_id = msg_obj.get('botId', None)
        datasource_id = msg_obj.get('datasourceId', None)
        datasources = msg_obj.get('datasources', None)
        
        log_metadata = {"bot_id":bot_id,"datasource_id":datasource_id }
        
        # Remove qa log
        # if datasources and 'qa' in datasources:
        #     datasources.pop('qa')
        

        # logger.info("Received Job from Kafka for bot: %s", bot_id, extra={"metadata": {**log_metadata,**(datasources or {})}})

        # Handle different data sources separately
        all_chunks = await aggregate_results(bot_id,datasource_id, datasources)

        # Check if all_chunks has any content
        if all_chunks:  # More Pythonic way to check if list is not empty
            collection_id = database_instance.create_or_return_collection_uuid(bot_id)
            logger.info("Collection ID created: %s", collection_id)

            embedded_chunks = create_document_embedding(all_chunks)

            database_instance.bulk_insert_embedding_record(
                bot_id=bot_id,
                records=all_chunks,
                embeddings=embedded_chunks,
                collection_id=collection_id
            )
            
            

            logger.info("Successfully processed and stored data for bot: %s s", bot_id  ,extra={"metadata": log_metadata})
        else:
            logger.warning("No chunks were generated for bot: %s", bot_id ,extra={"metadata": log_metadata})

    except Exception as e:
        logger.error("Error handling the job for bot: %s ", bot_id ,extra={"metadata": log_metadata}, exc_info=True)
        raise e


def create_rabbitmq_connection(config):
    """Creates a RabbitMQ connection with retry logic until successful."""
    connection = None
    while not connection:
        try:
            # Setup RabbitMQ connection
            credentials = pika.PlainCredentials(config['username'], config['password'])
            parameters = pika.ConnectionParameters(
                host=config['host'],
                virtual_host=config['virtual_host'],
                credentials=credentials
            )
            connection = pika.BlockingConnection(parameters)
            logger.info("RabbitMQ connection successful")
        except Exception as e:
            logger.error("RabbitMQ connection failed: %s", e)
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)
    
    return connection

def consume_jobs(channel, queue):
    """Consumes messages from RabbitMQ queue."""
    logger.info("Connected to RabbitMQ queue: %s", queue)
    
    def callback(ch, method, properties, body):
        try:
            # received_msg = body.decode('utf-8')
            # msg_for_log = json.loads(received_msg)
            
            original_message = body.decode('utf-8')
            original_message_json = json.loads(original_message)  # Parse the JSON


            received_msg = original_message_json["data"]
            msg_for_log = original_message_json["data"]

            if "datasources" in msg_for_log and "qa" in msg_for_log["datasources"]:
                del msg_for_log["datasources"]["qa"]

            logger.info("Received Message As Object: %s", msg_for_log)
            logger.info("Event received from RabbitMQ", extra={"metadata": str(msg_for_log)})

            # Extract information from the message
            event_type = received_msg.get('event_type', None)
            bot_id = received_msg.get('botId', None)
            datasource_id = received_msg.get('datasourceId', None)
            datasources = received_msg.get('datasources', None)
            
            if bot_id is None or datasource_id is None or datasources is None:
                logger.warning("Skipping job due to malformed data")
                return  # Exit the callback early
            
            elif event_type in {"update", "create"}:
                logger.info("Processing 'update' or 'create' event: botId=%s, datasourceId=%s, event_type=%s",
                            bot_id, datasource_id, event_type)
                asyncio.run(handle_incoming_job_events(received_msg))

            elif event_type == "qa_update":
                logger.info("Processing 'qa_update' event: botId=%s, datasourceId=%s", bot_id, datasource_id)
                asyncio.run(handle_incoming_job_events(received_msg))

        except Exception as e:
            # Activate Bot Even on Error
            if bot_id:
                database_instance.activate_loading_state(bot_id)
            logger.error("Error handling RabbitMQ job: %s", e, exc_info=True)

    # Start consuming messages from RabbitMQ
    channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
    logger.info("Started consuming messages from RabbitMQ")
    channel.start_consuming()

if __name__ == "__main__":

    # Connect to the database (assumed)
    database_instance.connect()

    # Log worker start message
    logger.info("Worker service started!")

    # Create RabbitMQ connection and channel
    connection = create_rabbitmq_connection(rabbitmq_conf)
    channel = connection.channel()

    # Declare the queue (make sure the queue exists)
    channel.queue_declare(queue=rabbitmq_conf['queue'], durable=True)

    # Start consuming messages from the queue
    consume_jobs(channel, rabbitmq_conf['queue'])

    # Close the connection (This will never be reached due to `start_consuming` blocking)
    connection.close()
    queue_listener.stop()