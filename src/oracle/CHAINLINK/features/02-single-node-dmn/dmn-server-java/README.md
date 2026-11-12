# Java DMN decision engine server

This Java 17 and Spring Boot service evaluates DMN decision tables and returns decision metadata. The single-node Chainlink workflow can call it over HTTP.

## Build and run

From this directory, with JDK 17 and Maven:

```bash
mvn clean package -DskipTests
bash ../start-dmn-server-java.sh
curl --fail http://127.0.0.1:8080/api/dmn/health
```

Use `bash ../status-dmn-server-java.sh` to inspect the service and `bash ../stop-dmn-server-java.sh` to stop it. Server settings are defined in the application's Spring Boot configuration.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/dmn/health` | Service health |
| `POST /api/dmn/evaluate` | Evaluate the decision identified by `decisionId` using `dmnContent` and `inputData` |
| `POST /api/dmn/input-info` | Inspect inputs and decisions in `dmnContent` |

Use the actual DMN XML and matching decision identifier in each request.
