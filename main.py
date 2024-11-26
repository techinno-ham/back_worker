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
logger, queue_listener = setup_logging()

load_dotenv(override=True)

consumer_conf = {'bootstrap.servers': os.getenv("KAFKA_SERVER"),
                 'security.protocol': 'SASL_SSL',
                 'sasl.mechanism': os.getenv('KAFKA_SASL_MECH'),
                 'sasl.username': os.getenv("KAFKA_USERNAME"),
                 'sasl.password': os.getenv("KAFKA_PASS"),
                 'group.id': os.getenv("KAFKA_GROUP_ID"),
                 'auto.offset.reset': os.getenv("KAFKA_OFFSET_RESET")}


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
        
        all_chunks = await handle_qa_update(bot_id,datasource_id, datasources)

        # Check if all_chunks has any content
        if all_chunks:  # More Pythonic way to check if list is not empty
            collection_id = database_instance.return_collection_uuid1(bot_id)
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
        msg = consumer.poll(0.5)

        if msg is None:
            #print("Pulled Message:",msg)
            continue
        if msg.error():
            logger.error("Kafka consumer error: %s", msg.error(),exc_info=True)
            continue
        try:
            received_msg = msg.value()
            
            msg_for_log = json.loads(received_msg)           
            if "datasources" in msg_for_log and "qa" in msg_for_log["datasources"]:
                #del msg_for_log["datasources"]["text"]
                del msg_for_log["datasources"]["qa"]
                
            print("Recieved Message As Object:" , msg_for_log)
            
            logger.info("Event revieved from kafka",extra={"metadata": str(msg_for_log)})
            
            msg_obj = json.loads(received_msg)
            
            
            event_type = msg_obj.get('event_type', None)
            bot_id = msg_obj.get('botId', None)
            datasource_id = msg_obj.get('datasourceId', None)
            datasources = msg_obj.get('datasources', None)
            
            if bot_id is None or datasource_id is None or datasources is None:
                logger.warning("Skipping job due to Malform data" )
                continue  # Exit the function early
            
            elif event_type in {"update", "create"}:
                logger.info("Processing 'update' or 'create' event: botId=%s, datasourceId=%s, event_type=%s",
                bot_id, datasource_id, event_type)
                asyncio.run(handle_incoming_job_events(msg_obj))

            elif event_type == "qa_update":
                logger.info("Processing 'qa_update' event: botId=%s, datasourceId=%s", bot_id, datasource_id)
                asyncio.run(handle_incoming_job_events(msg_obj))

            # Run the async function in a new event loop
            # asyncio.run(handle_incoming_job_events(msg_obj))
            # logger.info("Event handled successfully" ,extra={"metadata": msg})
        except Exception as e:
            logger.error("Error handling kafka job: %s", e , exc_info=True)


if __name__ == "__main__":

    database_instance.connect()
    
    logger.info("Worker service started !")
    
    database_instance.connect()

    consumer = create_kafka_consumer(consumer_conf)

    consume_jobs(consumer, os.getenv("KAFKA_TOPIC"))

    consumer.close()
    
    queue_listener.stop()
