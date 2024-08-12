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


def crawl_and_extract(bot_id, links):
    collection_id = database_instance.create_or_return_collection_uuid(bot_id)

    for link in links:
        print("Now in link:", link)
        try:
            # page = requests.get(link)
            # soup = BeautifulSoup(page.text, 'html.parser')
            # text = soup.get_text(separator='\n', strip=True)
            # print(text)

            loader = RecursiveUrlLoader(
                url=link, max_depth=1, extractor=lambda x: Soup(x, "html.parser").text
            )
            docs = loader.load();

            chunked_docs = recursive_char_splitter(docs)

            embedded_chunks = create_document_embedding(chunked_docs)

            for index, chunk in enumerate(chunked_docs):
                database_instance.insert_embedding_record(bot_id=bot_id,
                                                          content=chunk.page_content,
                                                          metadata=chunk.metadata,
                                                          embedding=embedded_chunks[index],
                                                          collection_id=collection_id
                                                          )

            print(f"Successfully crawled and extracted from: {link}")
        except Exception as e:
            print(f"Error crawling {link}: {e}")


async def aggregate_results(datasources):
    tasks = []

    # ok
    if 'text' in datasources:
        tasks.append(handle_text_datasource(datasources['text']))
    # ok
    if 'qa' in datasources:
        tasks.append(handle_qa_datasource(datasources['qa']))
    # not ok
    if 'urls' in datasources:
        tasks.append(handle_urls_datasource(datasources['urls']))
    # not ok
    if 'files' in datasources:
        tasks.append(handle_files_datasource(datasources['files']))

    all_chunks = await asyncio.gather(*tasks)

    # print(1111,all_chunks[0])
    # print(2222, all_chunks[1])
    # print(3333, all_chunks[2])
    # print(4444, all_chunks[3])

    flattened_list = [item for sublist in all_chunks for item in sublist]

    return flattened_list


async def handle_incoming_job_events(job):
    # received_msg = job.value()
    # msg_obj = jso n.loads(received_msg)

    bot_id = "dbef3edd-b2cc-4e44-bc08-d0e5945bad2c"

    # Define the datasources as given
    datasources = {
        "text": "Sample text inputSample text . Sample text inputSample text inputSample text inputSample text "
                "inputSample text inputSample text inputSample text inputSample text inputSample text inputSample "
                "text inputSample text inputSample text inputSample text inputSample text inputSample text "
                "inputSample text inputSample text inputSample text inputSample text inputSample text inputSample "
                "text inputSample text inputSample text inputSample text inputSample text inputSample text "
                "inputSample text input. Sample text inputSample text inputSample text inputSample text inputSample "
                "text inputSample text inputSample text inputSample text inputSample text inputSample text "
                "inputSample text inputSample text inputSample text inputSample text inputSample text inputSample "
                "text inputSample text inputSample text inputSample text inputSample text inputSample text "
                "inputSample text inputSample text inputSample text inputSample text inputSample text inputSample "
                "text input",
        "qa": [{
            "question": "Sample Q&A input",
            "answer": "Sample txt goes here"
        }, {
            "question": "Sample Q&A input",
            "answer": "Sample txt goes here"
        }],
        "urls": ["http://plotset.com"],
        "files": ["../"]
    }

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

    # Need improvment , sends several request to DB
    # for index, chunk in enumerate(chunked_docs):
    #     database_instance.insert_embedding_record(bot_id=bot_id,
    #                                               content=chunk.page_content,
    #                                               metadata=chunk.metadata,
    #                                               embedding=embedded_chunks[index],
    #                                               collection_id=collection_id
    #                                               )


async def consume_jobs(consumer, topic):
    # consumer.subscribe([topic])

    print("Connected to topic:", topic)

    # while True:
    #     msg = consumer.poll(1.0)
    #
    #     if msg is None:
    #         continue
    #     if msg.error():
    #         print("Consumer error: {}".format(msg.error()))
    #         continue
    #
    #     handle_incoming_job_events(msg)
    #
    #     crawl_and_extract(bot_id, url_list)

    bot_id = "123456887"

    # Define the datasources as given
    datasources = {
        "text": "Sample text input",
        "qa": "Sample Q&A input",
        "urls": ["http://plotset.com", ],
        "files": ["'../"]
    }

    # Create the mock message object
    mock_msg = {
        "bot_id": bot_id,
        "datasources": datasources
    }

    await handle_incoming_job_events(mock_msg)


if __name__ == "__main__":
    database_instance.connect()

    # data = database_instance.fetch_data("SELECT * FROM BOTS;");
    # for row in data:
    #     print(row)

    # consumer = Consumer(consumer_conf)

    asyncio.run(consume_jobs(None, 'aqkjtrhb-default'))

    # with database_instance as db:
    #     db.execute_query("SELECT * FROM bots")
    #     data = db.fetch_data("SELECT * FROM bots")
    #     for row in data:
    #         print(row)
    # consumer.close()
