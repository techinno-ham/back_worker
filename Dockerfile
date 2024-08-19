#https://medium.com/@albertazzir/blazing-fast-python-docker-builds-with-poetry-a78a66f5aed0



# # Use an official Python runtime as a parent image
# FROM python:3.11-buster

# RUN pip install poetry

# # Set the working directory in the container
# WORKDIR /app

# ARG DB_NAME
# ARG DB_HOST
# ARG DB_USER
# ARG DB_PORT
# ARG DB_PASS
# ARG KAFKA_USERNAME
# ARG KAFKA_PASS
# ARG KAFKA_GROUP_ID
# ARG OPENAI_API_KEY

# # Set environment variables from build arguments
# ENV DB_NAME=$DB_NAME
# ENV DB_PASS=$DB_PASS
# ENV DB_USER=$DB_USER
# ENV DB_PORT=$DB_PORT
# ENV DB_HOST=$DB_HOST
# ENV KAFKA_USERNAME=$KAFKA_USERNAME
# ENV KAFKA_PASS=$KAFKA_PASS
# ENV KAFKA_GROUP_ID=$KAFKA_GROUP_ID
# ENV OPENAI_API_KEY=$OPENAI_API_KEY
# # Copy the current directory contents into the container at /app
# COPY . /app

# RUN poetry install --no-root

# # Make port 8000 available to the world outside this container
# # EXPOSE 8000

# # Run app.py when the container launches
# CMD ["poetry" , "run", "python", "main.py"]


# #WORKING OPTIMIZED VERSION=======================================================================================
# The builder image, used to build the virtual environment
FROM python:3.12-bookworm as builder

# Install build dependencies
# RUN apt-get update \
#     && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# Install a specific version of Poetry
RUN pip install poetry==1.7.1

# Set Poetry environment variables to optimize the build
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set the working directory in the builder image
WORKDIR /app

# Copy only the dependency management files
COPY pyproject.toml ./

# Add a placeholder README to avoid potential errors with Poetry
RUN touch README.md

# Install dependencies without development dependencies and clean up cache
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.12-slim-bookworm as runtime

#Show Python logs immediately
ENV PYTHONUNBUFFERED=1

ARG DB_NAME
ARG DB_HOST
ARG DB_USER
ARG DB_PORT
ARG DB_PASS
ARG KAFKA_SERVER
ARG KAFKA_TOPIC
ARG KAFKA_USERNAME
ARG KAFKA_PASS
ARG KAFKA_GROUP_ID
ARG KAFKA_SASL_MECH
ARG KAFKA_OFFSET_RESET
ARG OPENAI_API_KEY

# Set environment variables from build arguments
ENV DB_NAME=$DB_NAME
ENV DB_PASS=$DB_PASS
ENV DB_USER=$DB_USER
ENV DB_PORT=$DB_PORT
ENV DB_HOST=$DB_HOST
ENV KAFKA_SERVER=$KAFKA_SERVER
ENV KAFKA_TOPIC=$KAFKA_TOPIC
ENV KAFKA_USERNAME=$KAFKA_USERNAME
ENV KAFKA_PASS=$KAFKA_PASS
ENV KAFKA_GROUP_ID=$KAFKA_GROUP_ID
ENV KAFKA_SASL_MECH=$KAFKA_SASL_MECH
ENV KAFKA_OFFSET_RESET=$KAFKA_OFFSET_RESET
ENV OPENAI_API_KEY=$OPENAI_API_KEY

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up the virtual environment path and adjust the PATH environment variable
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy the virtual environment from the builder image
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# RUN pip install poetry==1.7.1

# # Set the working directory in the container
WORKDIR /app

# # Copy the current directory contents into the container at /app
COPY . /app

# Set the entry point to run the application
#ENTRYPOINT ["sleep" , "infinity"]
ENTRYPOINT ["python" , "main.py"]

