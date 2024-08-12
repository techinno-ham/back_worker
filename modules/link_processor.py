import asyncio
from bs4 import BeautifulSoup as Soup
from utils import recursive_char_splitter
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader


async def crawl_and_extract(link):
    try:
        # page = requests.get(link)
        # soup = BeautifulSoup(page.text, 'html.parser')
        # text = soup.get_text(separator='\n', strip=True)
        # print(text)

        loader = RecursiveUrlLoader(
            url=link, max_depth=1 , timeout=4, extractor=lambda x: Soup(x, "html.parser").text
        )
        docs = loader.load()

        chunked_docs = recursive_char_splitter(docs)

        return chunked_docs

    except Exception as e:
        print(f"Error crawling {link}: {e}")
        return None


async def handle_urls_datasource(urls):
    tasks = []
    for url in urls:
        tasks.append(crawl_and_extract(url))
        print("Now in link:", url)

    all_chunks = await asyncio.gather(*tasks)

    all_chunks_flat = [item for sublist in all_chunks if sublist is not None for item in sublist]

    print(f"Processed URLs: {all_chunks_flat}")

    return all_chunks_flat

