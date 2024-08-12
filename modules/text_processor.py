from langchain.docstore.document import Document
from utils import recursive_char_splitter


async def handle_text_datasource(text):
    document = [Document(page_content=text, metadata={"source": "local"})]
    print(f"Processed text: {text}")
    splited_docs = recursive_char_splitter(document)
    return splited_docs
