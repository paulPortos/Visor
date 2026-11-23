FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Browser requests go through Nginx on the same origin as the frontend.
ENV VITE_API_BASE_URL=/ \
    VITE_API_VERSION=v1 \
    VITE_WS_BASE_URL=
RUN npm run build

FROM nginx:1.28-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
