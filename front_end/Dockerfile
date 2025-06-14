# Dockerfile for Vite React frontend
FROM node:20-alpine as build
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM node:20-alpine as serve
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
