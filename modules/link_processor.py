import asyncio
from bs4 import BeautifulSoup as Soup
from utils import recursive_char_splitter
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader

import logging

# Load the logging configuration
logger = logging.getLogger()

async def handle_urls_datasource(urls, log_metadata=None):
    """Handle a list of URLs, crawl and extract text from each."""
    logger.info("LINKS: datasource processing started", extra={"metadata": log_metadata})

    try:
        tasks = []
        for url in urls:
            tasks.append(crawl_and_extract(url, log_metadata))

        all_chunks = await asyncio.gather(*tasks)

        # Flatten the list of lists and filter out None results
        all_chunks_flat = [item for sublist in all_chunks if sublist is not None for item in sublist]

        logger.info(f"LINKS: successfully processed: {urls}", extra={"metadata": log_metadata})
        return all_chunks_flat

    except Exception as e:
        logger.error(f"LINKS: error processing : {urls}", exc_info=True, extra={"metadata": log_metadata})
        return []


async def crawl_and_extract(link, log_metadata=None):
    """Crawl a URL and extract text, then split into chunks."""
    # logger.info(f"Starting crawl for URL: {link}", extra={"metadata": log_metadata})
    
    try:
        # Initialize the URL loader with the given link
        loader = RecursiveUrlLoader(
            url=link, max_depth=1, timeout=4, extractor=lambda x: Soup(x, "html.parser").text
        )
        docs = loader.load()
        
        # Apply chunking logic
        chunked_docs = recursive_char_splitter(docs)

        # logger.info(f"Successfully crawled and extracted text from URL: {link}", extra={"metadata": log_metadata})
        return chunked_docs

    except Exception as e:
        logger.error(f"LINKS: error crawling URL: {link}", exc_info=True, extra={"metadata": log_metadata})
        return None


