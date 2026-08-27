# syntax=docker/dockerfile:1
FROM eclipse-temurin:17-jdk-alpine AS build

WORKDIR /app
COPY src ./src

RUN mkdir out \
    && javac --release 17 -encoding UTF-8 \
        -d out src/br/com/mecaniqa/Application.java \
    && jar --create --file app.jar \
        --main-class br.com.mecaniqa.Application \
        -C out .

FROM eclipse-temurin:17-jre-alpine

RUN addgroup -S mecaniqa \
    && adduser -S -G mecaniqa mecaniqa

WORKDIR /app
COPY --from=build --chown=mecaniqa:mecaniqa /app/app.jar ./app.jar

USER mecaniqa
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/health || exit 1

CMD ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
