# Etapa 1: Build (Gera os arquivos otimizados)
FROM node:20-alpine AS builder

WORKDIR /app

# Copia os arquivos de dependências e instala
COPY package*.json ./
RUN npm install

# Copia o restante do código React e compila
COPY . .
RUN npm run build

# Etapa 2: Servidor Web (Nginx)
FROM nginx:alpine

# Copia os arquivos gerados no build para a pasta pública do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração customizada de rotas
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]