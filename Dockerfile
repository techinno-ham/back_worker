#https://medium.com/@albertazzir/blazing-fast-python-docker-builds-with-poetry-a78a66f5aed0



# Use an official Python runtime as a parent image
FROM python:3.11-buster

RUN pip install poetry

# Set the working directory in the container
WORKDIR /app

ARG DB_NAME
ARG DB_HOST
ARG DB_USER
ARG DB_PORT
ARG DB_PASS
ARG KAFKA_USERNAME
ARG KAFKA_PASS
ARG KAFKA_GROUP_ID
ARG OPENAI_API_KEY

# Set environment variables from build arguments
ENV DB_NAME=$DB_NAME
ENV DB_PASS=$DB_PASS
ENV DB_USER=$DB_USER
ENV DB_PORT=$DB_PORT
ENV DB_HOST=$DB_HOST
ENV KAFKA_USERNAME=$KAFKA_USERNAME
ENV KAFKA_PASS=$KAFKA_PASS
ENV KAFKA_GROUP_ID=$KAFKA_GROUP_ID
ENV OPENAI_API_KEY=$OPENAI_API_KEY
# Copy the current directory contents into the container at /app
COPY . /app

RUN poetry install --no-root

# Make port 8000 available to the world outside this container
# EXPOSE 8000

# Run app.py when the container launches
CMD ["poetry" , "run", "python", "main.py"]
