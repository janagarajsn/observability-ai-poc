FROM python:3.11.9-slim

# Set working directory
WORKDIR /app/src

# Copy requirements file
COPY requirements.txt ../

# Install dependencies
RUN pip install --no-cache-dir -r ../requirements.txt

# Copy application code
COPY src/ .

EXPOSE 8000 8501

CMD ["bash", "-c", "echo 'Run your services'"]