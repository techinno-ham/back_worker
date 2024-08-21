from langchain.docstore.document import Document


async def handle_qa_datasource(qa):
    documents = []
    for item in qa:
        question = item.get('question', '')
        answer = item.get('answer', '')
        doc_content = f"Q: {question}\nA: {answer}"
        document = Document(page_content=doc_content, metadata={"source": "qa"})
        documents.append(document)
    return documents
