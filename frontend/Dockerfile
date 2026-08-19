FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app/.output ./.output
ENV NITRO_PORT=3000
ENV NITRO_HOST=0.0.0.0
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
