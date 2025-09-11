FROM python:3.12-slim

ARG INVESTMENT_ADVISOR_ARN
ARG MEMORY_ID
ARG AWS_REGION

ENV INVESTMENT_ADVISOR_ARN=$INVESTMENT_ADVISOR_ARN
ENV MEMORY_ID=$MEMORY_ID
ENV AWS_REGION=$AWS_REGION

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY investment_advisor/app.py .
COPY static ./static

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1


ENTRYPOINT [ "streamlit", "run", "app.py", \
             "--logger.level", "info", \
             "--browser.gatherUsageStats", "false", \
             "--browser.serverAddress", "0.0.0.0", \
             "--server.enableCORS", "false", \
             "--server.enableXsrfProtection", "false", \
             "--server.baseUrlPath", "/ia", \
             "--server.port", "80"]