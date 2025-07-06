FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y wget unzip chromium-driver chromium && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for Chrome/Chromedriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set workdir
WORKDIR /app

# Copy your code
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r "Monitor Linkedin fee/requirements.txt"

# Expose port if needed (for web apps)
# EXPOSE 8501

# Default command
CMD ["python", "Monitor Feed.py"]