from langchain.docstore.document import Document

import logging

# Load the logging configuration
logger = logging.getLogger()

async def handle_qa_datasource(qa, log_metadata=None):
    """Handle QA data and create Document objects from questions and answers."""

    logger.info("QA: processing started", extra={"metadata": log_metadata})
    documents = []

    try:
        for item in qa:
            question = item.get('question', '')
            answer = item.get('answer', '')
            doc_content = f"Q: {question}\nA: {answer}"
            document = Document(page_content=doc_content, metadata={"source": "qa"})
            documents.append(document)
        
        logger.info("QA: processing completed successfully", extra={"metadata": log_metadata})
        return documents

    except Exception as e:
        logger.error("QA: error processing ", exc_info=True, extra={"metadata": log_metadata})
        return []