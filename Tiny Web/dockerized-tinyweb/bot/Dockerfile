FROM node:20-slim

# Устанавливаем зависимости Playwright (Firefox)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && npx playwright install-deps firefox \
    && npx playwright install firefox \
    && apt-get clean

WORKDIR /app
COPY admin.js ./
COPY package.json ./

RUN npm install express playwright

ENV FLAG=GPNCTF{COd3_gO1f_15_Fun__FIr3FoX_FeAtuREs_TOO}

CMD ["node", "admin.js"]