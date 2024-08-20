from langchain_community.document_loaders.s3_directory import S3DirectoryLoader

# Initialize and load documents
directory_loader = S3DirectoryLoader(
    bucket='data-sources',  # Your bucket name
    prefix='9bee920e-59f2-4a32-8ed8-e6881ec6b0f9',  # The path within the bucket
    endpoint_url=f'http://84.46.250.91:9000',
    aws_access_key_id="yuNHWyFV3oeOZQtTyUDZ", 
    aws_secret_access_key="C189QC1beRrnqAN357vszwQk6FUBAAUC49eFhWAA", 
    
    # use_ssl=use_ssl
)

documents = directory_loader.load()

print(documents)