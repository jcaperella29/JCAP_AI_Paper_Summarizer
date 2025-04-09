# Use lightweight Python base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Set default port (Cloud Run expects $PORT)
ENV PORT=8080
EXPOSE 8080

# Start the Flask app
CMD ["python", "app.py"]
