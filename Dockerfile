# Node 18 LTS
FROM node:18-slim

WORKDIR /app

# copy package files first to cache deps
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# copy rest
COPY . .

# run as non-root for best practice
RUN useradd --user-group --create-home --shell /bin/false appuser \
  && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["npm", "start"]
