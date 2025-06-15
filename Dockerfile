FROM eclipse-temurin:21-jre-jammy

LABEL authors="elifececan"

WORKDIR /app

COPY target/bioinformatics-0.0.1-SNAPSHOT.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
