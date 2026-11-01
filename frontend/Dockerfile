# ─────────────────────────────────────────────────────────────
# 阶段一：构建（node）
# 这一阶段产物不会被保留，只有 dist/ 会被拷到下一阶段
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

# 先只拷依赖清单，利用层缓存：package.json 不变就不重装
COPY package.json package-lock.json ./

# 国内构建走镜像源；Dockerfile 本身保持通用
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm ci --registry=$NPM_REGISTRY

# 再拷源码并构建（tsc 类型检查 + vite 打包）
COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────
# 阶段二：运行（nginx）
# 最终镜像只有 nginx + 静态文件，没有 node、没有 node_modules（约 50MB）
# ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
