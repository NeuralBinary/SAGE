# SAGE for Hermes Agent

The Hermes adapter is standalone. It uses only the Python standard library and does not modify the Hermes installation tree.

## Source checkout

From the SAGE repository:

```bash
./integrations/hermes/install.sh
hermes plugins enable sage
```

The installer writes to `$HERMES_HOME/plugins/sage` when `HERMES_HOME` is set, otherwise to `~/.hermes/plugins/sage`.

## Hermes in Docker

The official Hermes container keeps mutable state under `/opt/data`. Run the installer on the host against the directory mounted there:

```bash
./integrations/hermes/install.sh "$HERMES_DATA_DIR"
```

Set these variables on the Hermes service:

```text
SAGE_URL=http://host.docker.internal:8080
SAGE_AGENT_ID=hermes-a
SAGE_WORKSPACE=default
```

Add Docker host-gateway resolution when SAGE runs on the Docker host:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Then recreate the Hermes container and enable SAGE:

```bash
docker exec "$HERMES_CONTAINER" hermes plugins enable sage
```

## GitHub release asset

The release asset `sage-hermes-plugin-v0.2.1.zip` contains the `sage/` plugin directory. Extract that directory into `$HERMES_HOME/plugins/`, set the SAGE environment variables, enable the plugin, and start a new Hermes session.

The adapter injects claimed SAGE context before a model turn, ACKs it after a completed turn, and exposes `sage_handoff` for raw structured application data. Semantic encoding remains owned by SAGE.
