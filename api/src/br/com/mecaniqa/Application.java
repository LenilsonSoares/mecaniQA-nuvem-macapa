package br.com.mecaniqa;

import br.com.mecaniqa.config.ServerConfig;
import br.com.mecaniqa.http.ApiServer;

public final class Application {
    private Application() {
    }

    public static void main(String[] args) throws Exception {
        ServerConfig config = ServerConfig.fromEnvironment();
        ApiServer server = ApiServer.create(config);
        server.start();

        Runtime.getRuntime().addShutdownHook(new Thread(server::stop));
        System.out.printf("MecaniQA API disponível na porta %d%n", config.port());
        server.await();
    }
}
