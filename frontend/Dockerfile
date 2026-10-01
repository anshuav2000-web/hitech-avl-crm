# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# CRM frontend: React (craco) compiled to static files, served by nginx.
# Stage 1 builds with production env vars; stage 2 ships only the output.
# ---------------------------------------------------------------------------

# ---------- build ----------
FROM node:20-alpine AS build
WORKDIR /app

# Baked into the bundle at build time, so it must be a public URL, never a secret.
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GENERCI_SKIP_AUTOINSTALL=true

COPY package.json package-lock.json* ./
# `npm ci` uses the lockfile and fails loudly on drift; fall back to `npm install`
# only when no lockfile was committed.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npm run build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/build /usr/share/nginx/html
# The template lands in nginx's templates directory, where the official image runs
# envsubst at startup. That keeps the upstream host configurable per deployment
# instead of hard-coded to a compose service name.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]