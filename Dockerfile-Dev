FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

COPY ./requirements.txt /app

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]