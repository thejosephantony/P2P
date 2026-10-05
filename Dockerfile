FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /build
COPY src/Main.java src/Main.java
RUN mkdir -p out dist && javac --release 17 -encoding UTF-8 -d out src/Main.java && jar --create --file dist/p2p.jar --main-class Main -C out .
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /build/dist/p2p.jar /app/p2p.jar
ENTRYPOINT ["java", "-jar", "/app/p2p.jar"]
CMD ["--help"]
