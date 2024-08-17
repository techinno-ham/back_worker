from langchain_community.document_loaders.s3_directory import S3DirectoryLoader

# Initialize and load documents
directory_loader = S3DirectoryLoader(
    bucket='772cb473-b3a5-449c-802c-91ad943aa9ff',
    endpoint_url=f'http://',
    aws_access_key_id="", 
    aws_secret_access_key="", 
    # use_ssl=use_ssl
)

documents = directory_loader.load()

print(documents)