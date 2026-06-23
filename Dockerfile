FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY academic_research/ ./academic_research/

ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "academic_research.agent_runtime_app:agent_runtime", "--host", "0.0.0.0", "--port", "8080"]
