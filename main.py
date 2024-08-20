from dotenv import load_dotenv
# import requests
# from bs4 import BeautifulSoup
from confluent_kafka import Consumer
from db import database_instance
# import socket
import json
# from utils import recursive_char_splitter
from embed import create_document_embedding
import asyncio
import os

from modules.qa_processor import handle_qa_datasource
from modules.s3_processor import handle_files_from_s3
from modules.link_processor import handle_urls_datasource
from modules.text_processor import handle_text_datasource

import time
from confluent_kafka import Consumer, KafkaException

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

    if 'text' in datasources:
        tasks.append(handle_text_datasource(datasources['text']))

    if 'qa' in datasources:
        tasks.append(handle_qa_datasource(datasources['qa']))

    if 'urls' in datasources:
        tasks.append(handle_urls_datasource(datasources['urls']))

    if 'files' in datasources:
        tasks.append(handle_files_from_s3(bot_id))

    all_chunks = await asyncio.gather(*tasks)

    flattened_list = [item for sublist in all_chunks for item in sublist]

    return flattened_list


async def handle_incoming_job_events(job):
    print("Handle called")
    received_msg = job.value()
    msg_obj = json.loads(received_msg)

    datasources = msg_obj['datasources']
    bot_id = msg_obj['botId']

    print(f'URLs received for Bot: {bot_id}')
    print(f'Received Datasources from Kafka: {datasources}')

    # Handle different data sources separately
    all_chunks = await aggregate_results(bot_id,datasources)

    collection_id = database_instance.create_or_return_collection_uuid(bot_id)

    embedded_chunks = create_document_embedding(all_chunks)

    database_instance.bulk_insert_embedding_record(bot_id=bot_id,
                                                   records=all_chunks,
                                                   embeddings=embedded_chunks,
                                                   collection_id=collection_id
                                                   )


def create_kafka_consumer(config):
    """Creates a Kafka consumer with retry logic until successful."""
    consumer = None
    while not consumer:
        try:
            consumer = Consumer(config)
            print("Kafka consumer connection successful")
        except KafkaException as e:
            print(f"Kafka consumer connection failed: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
    
    return consumer



def consume_jobs(consumer, topic):
    consumer.subscribe([topic])

    print("Connected to topic:", topic)

    while True:
        msg = consumer.poll(2)

        if msg is None:
            print("Pulled Message:",msg)
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        try:
            print("Job revieved:",msg)
            # Run the async function in a new event loop
            asyncio.run(handle_incoming_job_events(msg))
            print("Successfully handled message")
        except Exception as e:
            print("Error handling message: %s", e)


if __name__ == "__main__":
    
    print("Worker service started !")
    
    database_instance.connect()

    consumer = create_kafka_consumer(consumer_conf)

    consume_jobs(consumer, os.getenv("KAFKA_TOPIC"))

    consumer.close()
