# ---- Builder Stage ----
# Start with a Python version that includes build tools
FROM python:3.12-slim as builder

# Set the working directory in the container
WORKDIR /app

# Install poetry or any other dependency manager if you use one
# For pip, we'll just upgrade it
RUN pip install --upgrade pip

# Copy the requirements file into the container
COPY ./requirements.txt .

# Install the Python dependencies
# Using --no-cache-dir reduces layer size
RUN pip install --no-cache-dir -r requirements.txt


# ---- Final Stage ----
# Start with a smaller, more secure base image for the final container
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the installed packages from the builder stage
# This is the magic of the multi-stage build!
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code into the final container
# This assumes your FastAPI app is in a directory named 'api'
COPY ./api /app/api

# Expose the port the app will run on
EXPOSE 8000

# Define the command to run your application
# This tells Docker how to start the Uvicorn server for your FastAPI app
# It looks for the 'app' object in the 'main.py' file inside the 'api' module
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]