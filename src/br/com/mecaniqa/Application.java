package br.com.mecaniqa;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;

public final class Application {
    private Application() {
    }

    public static void main(String[] args) throws Exception {
        int port = readPort();
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0);

        server.createContext("/", exchange -> respond(exchange, 200,
                "{\"message\":\"MecaniQA API em execução\"}"));
        server.createContext("/health", exchange -> respond(exchange, 200,
                "{\"service\":\"mecaniqa-api\",\"status\":\"UP\"}"));
        server.start();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
        System.out.printf("MecaniQA API disponível na porta %d%n", port);
        new CountDownLatch(1).await();
    }

    private static int readPort() {
        String configuredPort = System.getenv("PORT");
        if (configuredPort == null || configuredPort.isBlank()) {
            return 8080;
        }

        try {
            int port = Integer.parseInt(configuredPort);
            return port >= 1 && port <= 65_535 ? port : 8080;
        } catch (NumberFormatException ignored) {
            return 8080;
        }
    }

    private static void respond(HttpExchange exchange, int status, String body)
            throws IOException {
        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
            status = 405;
            body = "{\"error\":\"method_not_allowed\"}";
        }

        byte[] response = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, response.length);
        try (var output = exchange.getResponseBody()) {
            output.write(response);
        }
    }
}
