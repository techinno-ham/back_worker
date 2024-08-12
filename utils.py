from langchain.text_splitter import RecursiveCharacterTextSplitter
from embed import create_document_embedding


# def chunk_documents(docs, file_type):

def recursive_char_splitter(docs):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(docs)


def insert_chunks_to_db_async(database_instance, chunk_info, chunked_docs):
    embedded_chunks = create_document_embedding(chunked_docs)
    for index, chunk in enumerate(chunked_docs):
        database_instance.insert_embedding_record(bot_id=chunk_info.bot_id,
                                                  content=chunk.page_content,
                                                  metadata=chunk.metadata,
                                                  embedding=embedded_chunks[index],
                                                  collection_id=chunk_info.collection_id
                                                  )
