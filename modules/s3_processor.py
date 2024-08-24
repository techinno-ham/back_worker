import asyncio
import logging
import PyPDF2
import os
import io
import boto3
from langchain.schema import Document
from utils import recursive_char_splitter
from dotenv import load_dotenv

import logging

# Load the logging configuration
logger = logging.getLogger()

load_dotenv(override=True)

# Initialize S3 client
s3 = boto3.client('s3', 
                  endpoint_url=os.getenv('MINIO_HOST'),
                  aws_access_key_id=os.getenv("MINIO_ACCESS_KEY_ID"), 
                  aws_secret_access_key=os.getenv("MINIO_SECRET_ACCESS_KEY"))

async def handle_files_from_s3(folder_name , log_metadata=None):
    """Handle files from S3 and apply chunking. - folder name is equal to data source id"""

    bucket_name = 'data-sources'

    logger.info(f"S3: start handling files from S3 bucket: {bucket_name}, folder: {folder_name}", extra={"metadata": log_metadata})

    try:
        # Define file types to process
        file_types = ['txt', 'doc', 'docx', 'pdf']
        
        # Download files from S3
        documents = await download_files_from_s3(bucket_name, folder_name, file_types)
        # Apply chunking logic
        if documents:
            splited_chunks = recursive_char_splitter(documents)
        else:
            splited_chunks = []
        
        logger.info(f"S3: processed files successfully from bucket: {bucket_name}, folder: {folder_name}", extra={"metadata": log_metadata})
        return splited_chunks
    
    except Exception as e:
        logger.error(f"S3: error handling files from S3: {e}", exc_info=True, extra={"metadata": log_metadata})
        return []

async def download_files_from_s3(bucket_name, folder_name, file_types):
    """Download files from S3 bucket based on file types."""
    documents = []
    
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_name):
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
        logger.error(f"S3: error extracting text from PDF: {e}")
        return ""
