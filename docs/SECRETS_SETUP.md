# Docker Secrets Configuration
# Place these files in /run/secrets/ directory or use docker stack deploy

# Create SECRET_KEY secret:
# echo "your-secure-random-string-min-32-chars" | docker secret create SECRET_KEY -

# Create POSTGRES_PASSWORD secret:
# echo "your-secure-db-password" | docker secret create POSTGRES_PASSWORD -

# Example deployment:
# docker secret create SECRET_KEY "$(openssl rand -base64 32)"
# docker secret create POSTGRES_PASSWORD "$(openssl rand -base64 16)"
