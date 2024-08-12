# Use an official Python runtime as a parent image
FROM python:3.11

RUN pip install poetry

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN poetry install --no-root

# Make port 8000 available to the world outside this container
# EXPOSE 8000

# Run app.py when the container launches
CMD ["poetry" , "run", "python", "main.py"]
