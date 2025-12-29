FROM node:25.1.0

RUN apt-get update && apt-get install -y chromium ca-certificates libnss3-tools \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r pptruser \
    && useradd -r -g pptruser -G audio,video pptruser \
    && mkdir -p /home/pptruser/Downloads \
    && chown -R pptruser:pptruser /home/pptruser

WORKDIR /app

COPY package*.json ./
ENV PUPPETEER_SKIP_DOWNLOAD=true
RUN npm install --omit=dev

COPY . .

USER pptruser

RUN mkdir -p /home/pptruser/.pki/nssdb \
    && certutil -A -d "sql:/home/pptruser/.pki/nssdb" -n "seccon" -t "CT,c,c" -i ./cert.crt

CMD ["index.js"]
