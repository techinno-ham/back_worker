# # with bind mount
# docker run -d --name hamworker -v /var/logs/hamworker:/app/logs 

# # with volume mount
# docker run -d --name hamworker -v hamworker-logs:/app/logs --restart unless-stopped  hamyarchat/worker:latest

# #with bind mount 
# docker run -d --name hamworker -v ./logs:/app/logs --restart unless-stopped  hamyarchat/worker:latest

# # see volume content
# docker run --rm -it -v hamworker-logs:/data alpine /bin/sh

docker kill hamlang
echo y | docker system prune
docker pull hamyarchat/langchain:latest
docker run -d --name hamlang -p 8000:8000 --restart unless-stopped  hamyarchat/langchain:latest
docker ps