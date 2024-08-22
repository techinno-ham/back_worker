from langchain.docstore.document import Document
from utils import recursive_char_splitter

import logging

# Load the logging configuration
logger = logging.getLogger()

async def handle_text_datasource(text , log_metadata=None):
    logger.info(f"Text processing started" , extra={"metadata":log_metadata})
    try:
        document = [Document(page_content=text, metadata={"source": "local"})]
        
        splited_docs = recursive_char_splitter(document)
        logger.info(f"Text processing successful" , extra={"metadata":log_metadata})
        return splited_docs
    
    except Exception as e:
        logger.error(f"Error processing the text: {text}", extra={"metadata":log_metadata} ,exc_info=True)
        return []

