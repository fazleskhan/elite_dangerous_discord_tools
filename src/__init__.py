"""Elite Dangerous Discord tools package.

[README:PROJECT_DESCRIPTION]
Python Discord bot and CLI utilities for route lookup, system inspection,
datasource import/export, and cache operations for Elite Dangerous GIS data.
[/README]

[README:GIS_DESCRIPTION]
The Elite Dangerous game models the Milky Way in 3D space. This project
provides GIS-oriented tools backed by EDGIS plus local datasource caching.

https://www.spansh.co.uk/dumps

https://edgis.elitedangereuse.fr/

https://github.com/elitedangereuse/edgis
[/README]

[README:DOCKER_IMAGE]
An image of this deployed app is available on DockerHub:

https://hub.docker.com/repository/docker/fazleskhan/public-images/tags/elite-dangerous-discord-tools/

The image externalizes configuration, logs, and database storage to
`/config`, `/logs`, and `/data`.
[/README]

[README:ENVIRONMENT]
* `DISCORD_TOKEN`: required Discord bot token for `discord_runner.py` and
  `EDDiscordBot.run()`
* `DATASOURCE_TYPE`: datasource backend (`tinydb` or `redis`), default `tinydb`
* `TINYDB_NAME`: TinyDB file path override (default `./data/ed_route.db`)
* `REDIS_URL`: required when `DATASOURCE_TYPE=redis`
* `REDIS_APP_NAME`: Redis key namespace prefix (default `eddt`)
* `REDIS_MAX_CONNECTIONS`: optional Redis connection pool size override
[/README]
"""

# Package marker for importable src modules.
