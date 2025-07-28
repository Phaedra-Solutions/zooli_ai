# Use official Python slim image for a smaller footprint
     FROM python:3.9-slim

     # Set working directory
     WORKDIR /app

     # Copy requirements file
     COPY requirements.txt .

     # Install dependencies, including uvicorn and python-dotenv
     RUN pip install --no-cache-dir -r requirements.txt

     # Copy the entire application directory
     COPY . .

     # Expose port 8000 (default for Uvicorn)
     EXPOSE 8000

     # Command to run the application with Uvicorn
     CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]