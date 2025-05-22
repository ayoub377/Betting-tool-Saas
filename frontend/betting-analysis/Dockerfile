# Build Stage
FROM node:18-alpine AS build
WORKDIR /app
COPY ./package*.json ./
RUN npm ci
RUN npm install -g @angular/cli
COPY . .
RUN npm run build -- --configuration production

# Serve Stage (using Nginx for production)
FROM nginx:alpine
COPY --from=build /app/dist/betting-analysis /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/betting-analysis/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
