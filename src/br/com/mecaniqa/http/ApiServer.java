package br.com.mecaniqa.http;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import br.com.mecaniqa.config.ServerConfig;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.CountDownLatch;

public final class ApiServer {
    private final HttpServer server;

    private ApiServer(ServerConfig config) throws IOException {
        server = HttpServer.create(new InetSocketAddress("0.0.0.0", config.port()), 0);
        server.createContext("/health", this::handleHealth);
        server.createContext("/", this::handleRoot);
    }

    public static ApiServer create(ServerConfig config) throws IOException {
        return new ApiServer(config);
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    public void await() throws InterruptedException {
        new CountDownLatch(1).await();
    }

    private void handleRoot(HttpExchange exchange) throws IOException {
        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
            JsonResponses.sendMethodNotAllowed(exchange);
            return;
        }

        if (!"/".equals(exchange.getRequestURI().getPath())) {
            JsonResponses.send(exchange, 404, "{\"error\":\"not_found\"}");
            return;
        }

        JsonResponses.send(exchange, 200, "{\"message\":\"MecaniQA API em execução\"}");
    }

    private void handleHealth(HttpExchange exchange) throws IOException {
        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
            JsonResponses.sendMethodNotAllowed(exchange);
            return;
        }

        JsonResponses.send(exchange, 200,
                "{\"service\":\"mecaniqa-api\",\"status\":\"UP\"}");
    }
}
