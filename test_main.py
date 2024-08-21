import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from your_module import aggregate_results, handle_incoming_job_events, create_kafka_consumer, consume_jobs

@pytest.mark.asyncio
@patch('your_module.handle_text_datasource', new_callable=AsyncMock)
@patch('your_module.handle_qa_datasource', new_callable=AsyncMock)
@patch('your_module.handle_urls_datasource', new_callable=AsyncMock)
@patch('your_module.handle_files_from_s3', new_callable=AsyncMock)
async def test_aggregate_results(mock_files, mock_urls, mock_qa, mock_text):
    # Setup the mock return values
    mock_text.return_value = ['text_chunk']
    mock_qa.return_value = ['qa_chunk']
    mock_urls.return_value = ['url_chunk']
    mock_files.return_value = ['file_chunk']
    
    datasources = {
        'text': 'text_data',
        'qa': 'qa_data',
        'urls': 'url_data',
        'files': 'file_data'
    }

    result = await aggregate_results('test_bot_id', datasources)

    assert result == ['text_chunk', 'qa_chunk', 'url_chunk', 'file_chunk']
    mock_text.assert_called_once_with('text_data')
    mock_qa.assert_called_once_with('qa_data')
    mock_urls.assert_called_once_with('url_data')
    mock_files.assert_called_once_with('test_bot_id')

@pytest.mark.asyncio
@patch('your_module.create_document_embedding')
@patch('your_module.database_instance')
@patch('your_module.aggregate_results', new_callable=AsyncMock)
async def test_handle_incoming_job_events(mock_aggregate, mock_db, mock_embedding):
    # Setup mock values
    mock_aggregate.return_value = ['chunk1', 'chunk2']
    mock_db.create_or_return_collection_uuid.return_value = 'test_collection_id'
    mock_embedding.return_value = ['embedding1', 'embedding2']

    # Mock the job object and its value method
    mock_job = MagicMock()
    mock_job.value.return_value = json.dumps({
        'botId': 'test_bot_id',
        'datasources': {
            'text': 'some_text_data'
        }
    })

    await handle_incoming_job_events(mock_job)

    mock_aggregate.assert_called_once_with('test_bot_id', {'text': 'some_text_data'})
    mock_db.create_or_return_collection_uuid.assert_called_once_with('test_bot_id')
    mock_embedding.assert_called_once_with(['chunk1', 'chunk2'])
    mock_db.bulk_insert_embedding_record.assert_called_once_with(
        bot_id='test_bot_id',
        records=['chunk1', 'chunk2'],
        embeddings=['embedding1', 'embedding2'],
        collection_id='test_collection_id'
    )

@patch('your_module.Consumer')
def test_create_kafka_consumer(mock_consumer):
    # Setup the mock Consumer
    mock_instance = MagicMock()
    mock_consumer.return_value = mock_instance

    config = {'some_config': 'value'}
    consumer = create_kafka_consumer(config)

    mock_consumer.assert_called_once_with(config)
    assert consumer == mock_instance

@patch('your_module.create_kafka_consumer')
@patch('your_module.asyncio.run')
@patch('your_module.handle_incoming_job_events', new_callable=AsyncMock)
def test_consume_jobs(mock_handle, mock_async_run, mock_create_consumer):
    mock_consumer = MagicMock()
    mock_message = MagicMock()
    
    # Mock consumer polling
    mock_consumer.poll.return_value = mock_message
    mock_create_consumer.return_value = mock_consumer

    # Set up the mock return for the message handling
    mock_message.error.return_value = None

    consume_jobs(mock_consumer, 'test_topic')

    mock_consumer.subscribe.assert_called_once_with(['test_topic'])
    mock_consumer.poll.assert_called()
    mock_async_run.assert_called_once_with(mock_handle(mock_message))
    mock_consumer.close.assert_called_once()

