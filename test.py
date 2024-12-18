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

import time
from confluent_kafka import Consumer, KafkaException

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

from logging_config import setup_logging

# Load the logging configuration
logger = setup_logging(log_file='app.log.jsonl')

load_dotenv(override=True)

consumer_conf = {'bootstrap.servers': os.getenv("KAFKA_SERVER"),
                 'security.protocol': 'SASL_SSL',
                 'sasl.mechanism': os.getenv('KAFKA_SASL_MECH'),
                 'sasl.username': os.getenv("KAFKA_USERNAME"),
                 'sasl.password': os.getenv("KAFKA_PASS"),
                 'group.id': os.getenv("KAFKA_GROUP_ID"),
                 'auto.offset.reset': os.getenv("KAFKA_OFFSET_RESET")}


async def aggregate_results(bot_id,datasources):
    tasks = []

    log_metadata = {
        'bot_id': bot_id,
        'datasource_id': '1234',
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


async def handle_incoming_job_events(job):
    try:
        # Mock message object (simulating the job received from Kafka)
        mock_msg_obj = {
            "botId": "454b55e8-b84d-4b2e-8a34-646e3cb5d45e",
            "datasourceId":"srffsr567890",
            "datasources": {
                "text": "Sample text input | Sample text input |Sample text input |Sample text input |Sample text input |Sample text input |",
                "qa": [
                    {"question": "What is AI?", "answer": "AI stands for Artificial Intelligence."},
                    {"question": "What is Python?", "answer": "Python is a programming language."},
                ],
                "urls": ["https://docs.plotset.com"],
                "files": "454b55e8-b84d-4b2e-8a34-646e3cb5d45e"
            }
        }

        bot_id = mock_msg_obj.get('botId', None)
        datasource_id = mock_msg_obj.get('datasourceId', None)
        datasources = mock_msg_obj.get('datasources', None)
        
        # Remove qa log
        if datasources and 'qa' in datasources:
            datasources.pop('qa')
        
        log_metadata = {"bot_id":bot_id,"datasource_id":datasource_id }

        logger.info("Received Job from Kafka for bot: %s", bot_id, extra={"metadata": {**log_metadata,**(datasources or {})}})

        # Handle different data sources separately
        all_chunks = await aggregate_results(bot_id, datasources)

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


def create_kafka_consumer(config):
    """Creates a Kafka consumer with retry logic until successful."""
    consumer = None
    while not consumer:
        try:
            consumer = Consumer(config)
            logger.info("Kafka consumer connection successful")
        except KafkaException as e:
            logger.info("Kafka consumer connection failed: %s",e)
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)
    
    return consumer



def consume_jobs(consumer, topic):
    consumer.subscribe([topic])

    logger.info("Connected to topic:%s", topic)

    while True:
        msg = consumer.poll(2)

        if msg is None:
            print("Pulled Message:",msg)
            continue
        if msg.error():
            logger.error("Kafka consumer error: %s", msg.error(),exc_info=True)
            continue
        try:
            logger.info("Event revieved from kafka",extra={"metadata": msg})
            
            # Run the async function in a new event loop
            asyncio.run(handle_incoming_job_events(msg))
            logger.info("Event handled successfully" ,extra={"metadata": msg})
        except Exception as e:
            logger.error("Error handling kafka job: %s", e , exc_info=True)


if __name__ == "__main__":
    
    logger, queue_listener = setup_logging()
    
    # Example log entries
    logger.info("This is an info message")
    logger.error("This is an error message", extra={"user": "example_user"})
    
    # Stop the QueueListener when done
    # queue_listener.stop()

    asyncio.run(handle_incoming_job_events(123))
    exit()

    database_instance.connect()
    
    logger.info("Worker service started !")
    
    database_instance.connect()

    consumer = create_kafka_consumer(consumer_conf)

    consume_jobs(consumer, os.getenv("KAFKA_TOPIC"))

    consumer.close()
