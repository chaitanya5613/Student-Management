# Start from a computer that already has Python 3.12
FROM python:3.12-slim

# work inside the /app folder
WORKDIR /app

# install the packages first (Docker caches this step)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy our code
COPY . .

# Start the API (0.0.0.0 = reachable from outside the container)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
