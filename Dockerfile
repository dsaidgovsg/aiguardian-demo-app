ARG PYTHON_VERSION=3.11.10-slim
ARG APP_VERSION=latest

#
# First build stage - All requirements
#
FROM python:${PYTHON_VERSION} AS builder-main

# Tesseract for OCR of image files
# RUN apt -y update && \
#    apt install -y tesseract-ocr

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt

#
# Final image
#
FROM python:${PYTHON_VERSION}

#######################################################################
###          Install python requirements requirements.txt           ###

# Copy installed models and packages from builder stage
COPY --from=builder-main /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

###                  End - Install python requirements              ###
#######################################################################

# Set environment variables (e.g., set Python to run in unbuffered mode)
ENV PYTHONUNBUFFERED 1

RUN groupadd -r -g 1001 appuser \
    && useradd -r -u 1001 -g 1001 -d /app appuser

WORKDIR /app

#######################################################################
###                  Copy necessary project files                   ###

COPY .chainlit ./.chainlit
COPY chainlit.md ./
COPY public ./public
COPY src ./

COPY --chmod=0755 scripts/entrypoint.sh .

RUN echo VERSION=$(tr -dc 0-9 </dev/urandom | head -c 2)$(date "+%m%d%H%M")$(tr -dc 0-9 </dev/urandom | head -c 2) > .env

# Change ownership of all files under current directory to 1001:1001
RUN chown -R 1001:1001 ./

###                 End - Copy necessary project files              ###
#######################################################################

USER 1001:1001

EXPOSE 8000

ENV PYTHONPATH=/app

ENTRYPOINT [ "/app/entrypoint.sh" ]

CMD ["python", "-m", "uvicorn", "apps.fastapi_chainlit_app:app", "--host", "0.0.0.0"]
