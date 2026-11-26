package br.com.mecaniqa.config;

public record ServerConfig(int port) {
    public static ServerConfig fromEnvironment() {
        String configuredPort = System.getenv("PORT");
        if (configuredPort == null || configuredPort.isBlank()) {
            return new ServerConfig(8080);
        }

        try {
            int port = Integer.parseInt(configuredPort);
            return new ServerConfig(port >= 1 && port <= 65_535 ? port : 8080);
        } catch (NumberFormatException ignored) {
            return new ServerConfig(8080);
        }
    }
}
