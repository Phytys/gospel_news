FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# Next bakes NEXT_PUBLIC_* at build. Default empty → same-origin /api (nginx). Local dev: pass http://localhost:8000.
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
