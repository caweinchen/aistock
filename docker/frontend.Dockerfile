FROM node:22-alpine AS build

ARG ALPINE_MIRROR=""
ARG NPM_REGISTRY=""

WORKDIR /app/frontend

RUN if [ -n "$ALPINE_MIRROR" ]; then \
    sed -i "s|https://dl-cdn.alpinelinux.org/alpine|$ALPINE_MIRROR|g" /etc/apk/repositories; \
  fi

COPY frontend/package*.json ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi \
  && npm ci

COPY frontend ./
RUN npx expo export --platform web --output-dir dist

FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
