FROM python:3.10-slim

WORKDIR /app

COPY requisitos.txt .
RUN pip install -r requisitos.txt

COPY monitor.py .

CMD ["python", "monitor.py"]