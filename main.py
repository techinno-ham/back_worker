from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from confluent_kafka import Consumer
from db import database_instance
import socket
import json
from utils import recursive_char_splitter
from embed import create_document_embedding
import asyncio
import os

from modules.qa_processor import handle_qa_datasource
from modules.file_processor import handle_files_datasource
from modules.link_processor import handle_urls_datasource
from modules.text_processor import handle_text_datasource

load_dotenv()

consumer_conf = {'bootstrap.servers': 'dory.srvs.cloudkafka.com:9094',
                 'security.protocol': 'SASL_SSL',
                 'sasl.mechanism': 'SCRAM-SHA-512',
                 'sasl.username': os.getenv("KAFKA_USERNAME"),
                 'sasl.password': os.getenv("KAFKA_PASS"),
                 'group.id': os.getenv("KAFKA_GROUP_ID"),
                 'auto.offset.reset': 'smallest'}


async def aggregate_results(datasources):
    tasks = []

    if 'text' in datasources:
        tasks.append(handle_text_datasource(datasources['text']))

    if 'qa' in datasources:
        tasks.append(handle_qa_datasource(datasources['qa']))

    if 'urls' in datasources:
        tasks.append(handle_urls_datasource(datasources['urls']))

    if 'files' in datasources:
        tasks.append(handle_files_datasource(datasources['files']))

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
    all_chunks = await aggregate_results(datasources)

    collection_id = database_instance.create_or_return_collection_uuid(bot_id)

    embedded_chunks = create_document_embedding(all_chunks)

    database_instance.bulk_insert_embedding_record(bot_id=bot_id,
                                                   records=all_chunks,
                                                   embeddings=embedded_chunks,
                                                   collection_id=collection_id
                                                   )


def consume_jobs(consumer, topic):
    consumer.subscribe([topic])

    print("Connected to topic:", topic)

    while True:
        msg = consumer.poll(0.3)

        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        try:
            # Run the async function in a new event loop
            asyncio.run(handle_incoming_job_events(msg))
            print("Successfully handled message")
        except Exception as e:
            print("Error handling message: %s", e)


if __name__ == "__main__":
    database_instance.connect()

    consumer = Consumer(consumer_conf)

    consume_jobs(consumer, 'aqkjtrhb-default')

    consumer.close()
