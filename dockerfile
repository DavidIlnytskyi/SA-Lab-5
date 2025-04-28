# Use the official Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY main.py .

# Install FastAPI and Uvicorn
RUN pip install fastapi uvicorn python-consul

# Expose the port that FastAPI will run on
EXPOSE 5000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
