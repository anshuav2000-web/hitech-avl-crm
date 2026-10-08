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
# `--legacy-peer-deps` is required, not a shortcut: the committed lockfile pins
# date-fns@4 while react-day-picker@8 declares a peer range of ^2.28 || ^3, so a
# plain `npm ci` aborts with ERESOLVE. date-fns is not imported anywhere in
# src/, and the app was developed and tested against the pinned versions, so
# relaxing the peer check keeps the exact dependency tree the lockfile records.
RUN if [ -f package-lock.json ]; then npm ci --legacy-peer-deps; else npm install --legacy-peer-deps; fi

COPY . .
RUN npm run build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

# Default backend host for Docker network / Coolify communication
ENV BACKEND_HOST=backend

COPY --from=build /app/build /usr/share/nginx/html
# The template lands in nginx's templates directory, where the official image runs
# envsubst at startup. That keeps the upstream host configurable per deployment
# instead of hard-coded to a compose service name.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]