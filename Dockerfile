FROM python:3.11-slim
WORKDIR /workspace
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
ENV PYTHONPATH=/workspace/code/parc_track
CMD ["make", "tiny-fixture"]
