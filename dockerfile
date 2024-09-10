FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Install necessary packages including Chrome browser
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxdamage1 \
    libgtk-3-0 \
    libgbm1 \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome browser
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Define environment variable
ENV DISPLAY=:99

# Set up Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade webdriver-manager

# Copy the rest of the application
COPY . .

# Install Serverless globally
RUN npm install -g serverless@3.34.0
RUN npm install serverless-offline serverless-offline-sqs serverless-offline-sqs-external

# List installed packages for debugging
RUN npm list -g --depth=0
RUN npm list --depth=0
RUN pip list

# Expose ports for both the Serverless framework and FastAPI
EXPOSE 3000
EXPOSE 8000

# Use shell form of CMD to ensure PATH is respected
CMD ["sh", "-c", "serverless --version && serverless print && serverless offline --host 0.0.0.0","uvicorn", "crud.handler:app","--port", "8000"]

