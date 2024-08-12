#https://medium.com/@varsha.rainer/document-loaders-in-langchain-7c2db9851123

from langchain_community.document_loaders import DirectoryLoader

md_loader = DirectoryLoader('../', glob="**/*.md|**/*.json")
json_loader = DirectoryLoader('../', glob="**/*.md|**/*.json")
general_loader = DirectoryLoader('../', glob="**/*.[txt|md]")
docs = general_loader.load()

len(docs)

print(docs)