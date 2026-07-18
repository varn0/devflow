---
name: run-services
description: Use when starting, stopping, or checking a project's dev services, or finding/tailing their logs, or clearing orphaned processes — in any project managed by devcli. Triggers include "start/run the app in dev", "is it running", "stop the services", "where are the logs", "tail the backend log", "port already in use".
user-invocable: true
argument-hint: [project name]
---

# Run Dev Services with devcli

`devcli` is the standard way dev services are run here. It starts a project's
services (frontends, backends, DBs) as native host processes from one command,
tracks their PIDs, and captures each service's stdout to its own log file.

**This skill is tool-scoped, not project-scoped.** It knows devcli, not any one
app. A project's own launch modes (packaged builds, which services exist, where
the *app's own* logs go) belong in that project's local skill — if one exists,
load it too: it decides *which mode the app is in*, this skill handles the
*devcli mechanics* once the answer is "devcli".

`devcli docs` is devcli's full reference — run it for any flag or behavior not
covered here rather than guessing.

## Discover the project

devcli is keyed by project name. Never assume it — look it up:

```bash
devcli list                                       # projects + services + state
grep -rl "$(pwd)" ~/.devcli/projects/*/config.yaml   # project owning this repo
cat ~/.devcli/projects/<project>/config.yaml      # services, commands, order, ports
```

A project only manages the services in its `config.yaml`. A service the app needs
but that isn't listed there (an optional TTS/worker sidecar, etc.) will NOT be
started by devcli — start it by the project's documented command.

## Start / status / stop

```bash
devcli up <project>                    # start all, in dependency/order
devcli up <project> --service api      # only named service(s), comma-separated
devcli list                            # running/stopped per service
ls ~/.devcli/projects/<project>/pids/  # a pid file per running service
devcli stop <project>                  # stop this project (--all for every project)
devcli cleanup --project <project>     # kill orphans + clear stale pids
```

Startup is sequential in dependency order; a cascade failure (one fails → the
rest never start) means fix the *first* failure, not the last log line. Empty
`pids/` means devcli believes nothing is running, even if a log was just touched.
Reach for `cleanup` on "port already in use" / zombie-process symptoms.

## Logs

Each service's stdout is captured to
`~/.devcli/projects/<project>/logs/<service>.log` — the filename is the **service
name** from config (e.g. `fastapi.log`), not a generic `api.log`.

```bash
devcli logs --list --project <project>           # every log: name, size, mtime, path
devcli logs <service> --project <project> -f     # follow (survives restarts)
devcli logs <service> --project <project> -n 200 # last N lines
```

A service whose start-command itself spawns another process has *two* log
surfaces: devcli's captured stdout, and any log the spawned process writes on its
own. The project-local skill knows the latter.

## Quick reference

| Goal | Command |
|------|---------|
| Find the project | `grep -rl "$(pwd)" ~/.devcli/projects/*/config.yaml` |
| Start everything | `devcli up <project>` |
| Start one service | `devcli up <project> --service <name>` |
| Is it running? | `devcli list` / `ls ~/.devcli/projects/<project>/pids/` |
| Follow a log | `devcli logs <service> --project <project> -f` |
| List all logs | `devcli logs --list --project <project>` |
| Stop | `devcli stop <project>` |
| Clear orphans/ports | `devcli cleanup --project <project>` |
| Full reference | `devcli docs` |
