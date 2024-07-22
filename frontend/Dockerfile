# build stage
FROM node:lts-alpine as build-stage
WORKDIR /app
COPY package*.json *.config.js index.html ./
RUN npm install
COPY public ./public/
COPY src ./src/
RUN npm run build


# production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
