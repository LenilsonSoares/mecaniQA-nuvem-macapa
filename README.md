# MecâniQA - Nuvem Macapá

Entrega do Encontro 1 de Computação em Nuvem: isolamento da API Java, do
MySQL e do Redis em containers independentes.

## Equipe

| Papel | Integrante |
| --- | --- |
| Piloto | Lenilson Dias Soares |
| Copiloto | Joab Nascimento |
| QA | Artur Maia |
| Arquiteto | Douglas Renan |
| Scrum Master | Kayky Ribeiro Souza |

## Decisões da equipe

### A anatomia da imagem

Usaremos `eclipse-temurin:17-jdk-alpine`, pois a versão Alpine é baseada em uma
distribuição Linux minimalista e gera imagens menores. Diferentemente de uma
máquina virtual, que executa um sistema operacional convidado completo, o
container compartilha o kernel da máquina hospedeira e consome menos recursos.

O Dockerfile usa um build em dois estágios: o JDK compila o código e a imagem
final contém apenas o JRE e o arquivo JAR.

### Isolamento e exposição

Usaremos `EXPOSE 8080` para documentar a porta da API e `-p 8080:8080` no
`docker run` para publicá-la. O comando
`CMD ["java", "-jar", "app.jar"]`, na forma executável, mantém o processo Java
em primeiro plano enquanto o container estiver ativo.

Também limitaremos CPU e memória de cada container. Sem esses limites, separar
os processos em containers não impede que um deles consuma todos os recursos do
host.

## 1. Construir a imagem Java

Com o Docker Desktop iniciado, execute na raiz do repositório:

```console
docker build -t mecaniqa-api:1.0 .
```

## 2. Executar os containers isoladamente

### API Java

```console
docker run -d --name mecaniqa-api --memory=256m --cpus=0.50 -p 8080:8080 mecaniqa-api:1.0
curl.exe http://localhost:8080/health
```

Resposta esperada:

```json
{"service":"mecaniqa-api","status":"UP"}
```

### MySQL

A senha abaixo é apenas para o teste local da atividade:

```console
docker run -d --name mecaniqa-mysql --memory=512m --cpus=1 -e MYSQL_ROOT_PASSWORD=mecaniqa-local -e MYSQL_DATABASE=mecaniqa -p 127.0.0.1:3306:3306 mysql:8.4
docker exec mecaniqa-mysql mysqladmin ping -h localhost -uroot -pmecaniqa-local
```

Resposta esperada: `mysqld is alive`.

### Redis

```console
docker run -d --name mecaniqa-redis --memory=128m --cpus=0.25 -p 127.0.0.1:6379:6379 redis:7.4-alpine
docker exec mecaniqa-redis redis-cli ping
```

Resposta esperada: `PONG`.

MySQL e Redis usam as imagens oficiais. Cada serviço possui seu próprio
container; não é necessário criar Dockerfiles que apenas repitam essas imagens.

## 3. Validar o ciclo de vida

```console
docker ps
docker stats --no-stream
docker stop mecaniqa-api
docker start mecaniqa-api
curl.exe http://localhost:8080/health
docker logs mecaniqa-api
```

Para encerrar e remover os containers criados no encontro:

```console
docker stop mecaniqa-api mecaniqa-mysql mecaniqa-redis
docker rm mecaniqa-api mecaniqa-mysql mecaniqa-redis
```

No Encontro 2, esses comandos individuais serão substituídos por um arquivo
`docker-compose.yml` com rede interna e volumes persistentes.
