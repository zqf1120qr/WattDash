# Stage 1: Build Vue application
FROM node:18-alpine AS build-stage
WORKDIR /workspace/frontend

# Copy dependencies manifest
COPY package*.json ./

# Install packages
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve static files with Nginx
FROM nginx:stable-alpine AS production-stage

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output from build-stage to Nginx public folder
COPY --from=build-stage /workspace/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
