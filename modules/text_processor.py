from langchain.docstore.document import Document
from utils import recursive_char_splitter

import logging

# Load the logging configuration
logger = logging.getLogger()

async def handle_text_datasource(text , log_metadata=None):
    logger.info(f"TEXT: processing started" , extra={"metadata":log_metadata})
    try:
        document = [Document(page_content=text, metadata={"source": "local"})]
        
        splited_docs = recursive_char_splitter(document)
        logger.info(f"TEXT: processing successful" , extra={"metadata":log_metadata})
        return splited_docs
    
    except Exception as e:
        logger.error(f"TEXT: error processing the text: {text}", extra={"metadata":log_metadata} ,exc_info=True)
        return []

