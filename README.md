1. **Build the Docker image**:
   ```bash
   docker build -t zooli_app .
   ```

2. **Run the Docker container**:
   ```bash
   docker run -p 8000:8000 zooli_app
   ```