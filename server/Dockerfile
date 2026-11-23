FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 visor \
    && useradd --uid 10001 --gid visor --create-home visor \
    && mkdir -p /var/lib/visor \
    && chown visor:visor /var/lib/visor

COPY --chown=visor:visor . .
ENV DJANGO_SECRET_KEY_FILE=/var/lib/visor/django_secret_key \
    GITHUB_TOKEN_ENCRYPTION_KEY_FILE=/var/lib/visor/github_token_encryption_key
USER visor

EXPOSE 8000

ENTRYPOINT ["python", "scripts/docker_entrypoint.py"]
CMD ["python", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
