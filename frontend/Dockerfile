# --- STAGE 1: The "Base" Stage ---
# Installs all dependencies
FROM node:20-alpine AS base
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install all dependencies (npm ci is faster and safer than npm install)
RUN npm ci

# --- STAGE 2: The "Dev" Stage ---
# This is what docker-compose will use (target: dev)
FROM base AS dev
WORKDIR /app

# Copy the rest of the source code
COPY . .

# The command to run the dev server
CMD ["npm", "run", "dev"]

# --- STAGE 3: The "Build" Stage ---
# This stage builds your app for production
FROM base AS builder
WORKDIR /app
COPY . .
RUN npm run build

# --- STAGE 4: The "Final" Stage ---
# This is the tiny, final image for production
FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production

# Copy only the necessary build artifacts from the "builder" stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
# This is the command to run your app in production
CMD ["npm", "run", "start"]