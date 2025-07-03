# ---- Builder Stage ----
FROM python:3.12-slim as builder

WORKDIR /app

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Final Stage ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code
COPY ./api /app/api
COPY ./init_db.py .

# Copy and set up the new entrypoint script
COPY ./docker-entrypoint.sh .
RUN chmod +x ./docker-entrypoint.sh

EXPOSE 8000

# This tells Docker to always run our script first.
# The script will then execute the CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]

# This is the main command that gets passed to the entrypoint script
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]