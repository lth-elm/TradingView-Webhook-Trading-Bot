FROM python:3.10.4-alpine3.15

WORKDIR /flask_k8s

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]