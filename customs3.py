import boto3
import PyPDF2
import io

# Initialize the S3 client
s3 = boto3.client('s3', 
                  endpoint_url='http://84.46.250.91:9000',
                  aws_access_key_id="", 
                  aws_secret_access_key="")

def download_files_from_s3(bucket_name, prefix):
    # List objects in the specified S3 path
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    documents = []
    
    for obj in response.get('Contents', []):
        file_key = obj['Key']
        
        # Download the file from S3
        file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)['Body']
        
        if file_key.endswith('.pdf'):
            # Process PDF files
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_obj.read()))
            pdf_text = ''
            for page in range(len(pdf_reader.pages)):
                pdf_text += pdf_reader.pages[page].extract_text()
            documents.append({'file_name': file_key, 'content': pdf_text})
        else:
            # Process other text files
            file_content = file_obj.read().decode('utf-8')
            documents.append({'file_name': file_key, 'content': file_content})
    
    return documents

# Load documents
documents = download_files_from_s3('data-sources', '9bee920e-59f2-4a32-8ed8-e6881ec6b0f9')

# Now you have the documents and can process them without using nltk
print(documents)
