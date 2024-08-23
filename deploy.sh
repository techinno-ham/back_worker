# with bind mount
docker run -d --name hamworker -v /var/logs/hamworker:/app/logs 

#with volume mount
docker run -d --name hamworker -v hamworker-logs:/app/logs