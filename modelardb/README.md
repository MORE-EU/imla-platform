## Docker

An environment that includes a local [MinIO](https://min.io/) instance and an edge node using the [MinIO](https://min.io/)
instance as the remote object store, can be set up using [Docker](https://docs.docker.com/). Note that since
[Rust](https://www.rust-lang.org/) is a compiled language and a more dynamic `modelardbd` configuration might be needed,
it is not recommended to use the [Docker](https://docs.docker.com/) environment during active development of `modelardbd`.
It is however ideal to use for experimenting with `modelardbd` or when developing components that utilize `modelardbd`.

Downloading [Docker Desktop](https://docs.docker.com/desktop/) is recommended to make maintenance of the created
containers easier. Once [Docker](https://docs.docker.com/) is set up, the [MinIO](https://min.io/) instance can be
created by running the services defined in [docker-compose-minio.yml](docker-compose-minio.yml). The services can
be built and started using the command:

```shell
docker compose -p modelardata-minio -f compose-minio.yml up
```

After the [MinIO](https://min.io/) service is created, a [MinIO](https://min.io/) client is used to initialize
the development bucket `modelardata`, if it does not already exist. [MinIO](https://min.io/) can be administered through
its [web interface](http://localhost:9001). The default username and password, `minioadmin`, can be used to log in.
A separate compose file is used for [MinIO](https://min.io/) so an existing [MinIO](https://min.io/) instance can be
used when `modelardbd` is deployed using [Docker](https://docker.com/), if necessary.

Similarly, the `modelardbd` instance can be built and started using the command:

```shell
docker compose -p modelardbd up
```

The instance can then be accessed using the Apache Arrow Flight interface at `grpc://127.0.0.1:9999`.
