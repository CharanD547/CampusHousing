FROM python:3.12-slim
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY src ./src
COPY data ./data
COPY CampusHousing-main/index.html ./CampusHousing-main/index.html
COPY CampusHousing-main/src ./CampusHousing-main/src
ENV PYTHONPATH=/app/src
ENV ROOMWISE_DATA_DIR=/app/var
RUN mkdir -p /app/var && chown -R 10001:10001 /app/var
USER 10001:10001
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8001/api/v1/health'); t=os.getenv('ROOMWISE_API_TOKEN'); r.add_header('Authorization','Bearer '+t) if t else None; urllib.request.urlopen(r,timeout=4)"
CMD ["python", "-m", "uvicorn", "roomwise.main:app", "--host", "0.0.0.0", "--port", "8001"]
