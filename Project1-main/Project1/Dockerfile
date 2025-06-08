# Use the official Python image
FROM python:3.13.1-slim

# Set the working directory
WORKDIR /Project1

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev gcc

# Copy the requirements file
COPY requirements.txt /Project1/

# Install Python dependencies with an increased timeout
RUN pip install --default-timeout=120 --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . /Project1/

# Expose port (if needed)
EXPOSE 5000

# Command to run the application
CMD ["python", "main.py"]
