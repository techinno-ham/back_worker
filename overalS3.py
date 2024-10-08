import asyncio
import logging
import PyPDF2
import os
import io
import boto3
from langchain.schema import Document
from utils import recursive_char_splitter
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize S3 client
s3 = boto3.client('s3', 
                  endpoint_url='http://84.46.250.91:9000',
                  aws_access_key_id=os.getenv("aws_access_key_id"), 
                  aws_secret_access_key=os.getenv("aws_secret_access_key"))

async def download_files_from_s3(bucket_name, prefix, file_types):
    """Download files from S3 bucket based on file types."""
    documents = []
    
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            file_key = obj['Key']
            if file_key.endswith(tuple(file_types)):
                file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)['Body']

                file_name = os.path.basename(file_key)
                
                if file_key.endswith('.pdf'):
                    # Extract text from PDF
                    pdf_text = extract_text_from_pdf(file_obj)
                    # Create a Document object and add it to the list
                    document = Document(
                        page_content=pdf_text,
                        metadata={"file_name": file_name, }
                    )
                    documents.append(document)
                else:
                    # Read text from other files
                    file_content = file_obj.read().decode('utf-8')
                    # Create a Document object and add it to the list
                    document = Document(
                        page_content=file_content,
                        metadata={"file_name": file_key}
                    )
                    documents.append(document)
    
    return documents

def extract_text_from_pdf(file_obj):
    """Extract text from a PDF file object using PyPDF2."""
    try:
        # Create a PdfReader object from the file-like object
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_obj.read()))
        pdf_text = ''
        
        # Iterate over each page in the PDF
        for page in pdf_reader.pages:
            # Extract text from the page
            page_text = page.extract_text()
            if page_text:
                pdf_text += page_text
        
        return pdf_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

async def handle_files_from_s3(folder_name):
    """Handle files from S3 and apply chunking. - folder name is equal to data source id"""

    bucket_name = 'data-sources'

    try:
        # Define file types to process
        file_types = ['txt', 'doc', 'docx', 'pdf']
        
        # Download files from S3
        print(777,bucket_name, folder_name,)
        documents = await download_files_from_s3(bucket_name, folder_name, file_types)
        # Apply chunking logic
        if documents:
            splited_chunks = recursive_char_splitter(documents)
        else:
            splited_chunks = []
        
        logger.info(f"Processed files from bucket: {bucket_name} {folder_name}")
        print(len(splited_chunks))
        return splited_chunks
    
    except Exception as e:
        logger.error(f"Error handling files from S3: {e}")
        return []

# Example usage
async def main():
    bucket_name = 'data-sources'
    prefix = '454b55e8-b84d-4b2e-8a34-646e3cb5d45e'
    chunks = await handle_files_from_s3(prefix)
    print(chunks)
    
# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
