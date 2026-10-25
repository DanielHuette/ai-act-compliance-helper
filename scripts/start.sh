#!/usr/bin/env bash
# Builds and starts the service with Docker Compose. Prerequisites are checked first so the user
# gets an actionable message instead of a raw Docker error, in German or English.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# COMPLIANCE_HELPER_LANG wins, else the system locale; anything but English falls back to German.
REQUESTED_LANG="${COMPLIANCE_HELPER_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}"
case "$REQUESTED_LANG" in
  [Ee][Nn]*) UI_LANG=en ;;
  *)         UI_LANG=de ;;
esac
export COMPLIANCE_HELPER_LANG="$UI_LANG"

t() {
  if [[ $UI_LANG == en ]]; then printf '%s' "$2"; else printf '%s' "$1"; fi
}

usage() {
  if [[ $UI_LANG == en ]]; then
    cat <<'EOF'
One command that builds and starts the AI Act Compliance Helper.

The script first checks the prerequisites and says what to do about each
gap, instead of passing on a Docker error message nobody can make sense of.

Usage:
  ./scripts/start.sh                 build and start
  ./scripts/start.sh --small         without the large search model (fast)
  ./scripts/start.sh --refresh       rebuild without the build cache
  ./scripts/start.sh --stop          stop

The German flags --klein and --stopp work as well.
EOF
  else
    cat <<'EOF'
Ein Befehl, der den Konformitätshelfer baut und startet.

Das Skript prüft erst, ob die Voraussetzungen da sind, und sagt bei jedem
Mangel, was zu tun ist — statt eine Fehlermeldung von Docker durchzulassen,
aus der niemand schlau wird.

Aufruf:
  ./scripts/start.sh                 bauen und starten
  ./scripts/start.sh --klein         ohne das große Suchmodell (schnell)
  ./scripts/start.sh --refresh       ohne Zwischenspeicher neu bauen
  ./scripts/start.sh --stopp         anhalten

Die englischen Schalter --small und --stop gehen ebenso.
EOF
  fi
}

# Color only on a terminal and without NO_COLOR (https://no-color.org).
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  RED=$'\033[1;31m'; GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'
  BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BOLD=''; RESET=''
fi

say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$YELLOW" "$RESET" "$*"; }
fail() { printf '%s✗%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

SMALL=0; REFRESH=0; STOP=0
for arg in "$@"; do
  case "$arg" in
    --small|--klein) SMALL=1 ;;
    --refresh)       REFRESH=1 ;;
    --stop|--stopp)  STOP=1 ;;
    -h|--help)       usage; exit 0 ;;
    *)               fail "$(t "Unbekannte Angabe: $arg. Hilfe mit --help." \
                               "Unknown option: $arg. Help with --help.")" ;;
  esac
done

printf '%s%s%s\n\n' "$BOLD" "$(t 'Konformitätshelfer' 'AI Act Compliance Helper')" "$RESET"

if ! command -v docker >/dev/null 2>&1; then
  fail "$(t "Docker ist nicht installiert. Zu holen unter https://docs.docker.com/get-docker/" \
            "Docker is not installed. Get it at https://docs.docker.com/get-docker/")"
fi

if ! docker info >/dev/null 2>&1; then
  fail "$(t "Docker ist installiert, läuft aber nicht. Auf dem Mac und unter
  Windows: Docker Desktop starten. Unter Linux: sudo systemctl start docker" \
            "Docker is installed but not running. On a Mac and on
  Windows: start Docker Desktop. On Linux: sudo systemctl start docker")"
fi
DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null \
  || t 'Fassung unbekannt' 'version unknown')
ok "$(t "Docker läuft ($DOCKER_VERSION)" "Docker is running ($DOCKER_VERSION)")"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "$(t "docker compose fehlt. Es gehört zu neueren Docker-Fassungen dazu;
  sonst nachinstallieren: https://docs.docker.com/compose/install/" \
            "docker compose is missing. It comes with recent Docker versions;
  otherwise install it: https://docs.docker.com/compose/install/")"
fi

if [[ $STOP -eq 1 ]]; then
  "${COMPOSE[@]}" down
  ok "$(t 'Angehalten.' 'Stopped.')"
  exit 0
fi

if [[ ! -f data/processed/corpus.jsonl ]]; then
  fail "$(t "Die Rechtstexte fehlen: data/processed/corpus.jsonl
  Erst bauen:  compliance-helper build-corpus --language de" \
            "The legal texts are missing: data/processed/corpus.jsonl
  Build them first:  compliance-helper build-corpus --language de")"
fi
UNIT_COUNT=$(wc -l < data/processed/corpus.jsonl | tr -d ' ')
ok "$(t "Rechtstexte da: $UNIT_COUNT Rechtsstellen" "Legal texts present: $UNIT_COUNT legal units")"

for INDEX_LANG in de en; do
  INFIX=""
  if [[ $INDEX_LANG != de ]]; then INFIX=".$INDEX_LANG"; fi
  if [[ -f data/processed/search_index$INFIX.meta.json.gz ]]; then
    ok "$(t "Suchbestand ($INDEX_LANG) da — der Dienst muss beim Start nicht rechnen" \
            "Search index ($INDEX_LANG) present — the service need not compute it at start")"
  else
    warn "$(t "Der Suchbestand ($INDEX_LANG) fehlt. Der Dienst baut ihn beim Start selbst;
  ohne das große Modell bedeutet das schlechtere Fundstellen.
  Besser vorher:  compliance-helper build-index --language $INDEX_LANG" \
              "The search index ($INDEX_LANG) is missing. The service builds it itself at start;
  without the large model that means poorer citations.
  Better beforehand:  compliance-helper build-index --language $INDEX_LANG")"
  fi
done

if [[ ! -f .env ]]; then
  warn "$(t "Keine .env vorhanden. Es gelten die Vorgaben.
  Für ein Sprachmodell:  cp .env.example .env  und Schlüssel eintragen." \
            "No .env present. The defaults apply.
  For a language model:  cp .env.example .env  and enter the keys.")"
fi

BUILD_CMD=("${COMPOSE[@]}" build)
[[ $REFRESH -eq 1 ]] && BUILD_CMD+=(--no-cache)

if [[ $SMALL -eq 1 ]]; then
  export WITH_SEARCH_MODEL=0
  export COMPLIANCE_HELPER_MEMORY="${COMPLIANCE_HELPER_MEMORY:-1g}"
  warn "$(t "Kleines Abbild: ohne das Modell bge-m3. Die Suche vergleicht dann
  nur Wörter, nicht Bedeutung. Für einen Prüflauf in Ordnung, für den
  Betrieb nicht." \
            "Small image: without the bge-m3 model. The search then compares
  only words, not meaning. Fine for a test run, not for
  production.")"
else
  export WITH_SEARCH_MODEL=1
  say ""
  say "$(t "Es wird gebaut. Beim ersten Mal dauert das lange: Einbettungsmodell
und Kreuzbewerter sind zusammen rund 7 Gigabyte groß und werden mit ins
Abbild gelegt, damit der Container später ohne Netz arbeiten kann." \
           "Building. The first time this takes long: the embedding model
and the cross-encoder are about 7 gigabytes together and go into the
image so that the container can work offline later.")"
fi

say ""
"${BUILD_CMD[@]}" || fail "$(t "Der Bau ist fehlgeschlagen. Die letzte Meldung oben sagt,
  woran es lag. Häufigste Ursachen: kein Netz beim Holen der Pakete, oder zu
  wenig Platz auf der Platte (für das große Abbild sind rund 12 Gigabyte frei
  nötig — nachsehen mit: docker system df)." \
                               "The build failed. The last message above says
  why. Most common causes: no network while fetching the packages, or too
  little disk space (the large image needs about 12 gigabytes free
  — check with: docker system df).")"

ok "$(t 'Abbild gebaut' 'Image built')"

UP_CMD=("${COMPOSE[@]}")
UP_CMD+=(up --detach)

"${UP_CMD[@]}" || fail "$(t "Der Start ist fehlgeschlagen. Protokoll ansehen mit:
  ${COMPOSE[*]} logs app" \
                            "The start failed. View the log with:
  ${COMPOSE[*]} logs app")"

PORT="${COMPLIANCE_HELPER_PORT:-8000}"
BASE_URL="http://127.0.0.1:${PORT}"

say ""
printf '%s ' "$(t 'Der Dienst fährt hoch' 'The service is starting')"
READY=0
for _ in $(seq 1 90); do
  if curl --fail --silent --max-time 2 "${BASE_URL}/health" >/dev/null 2>&1; then
    READY=1; break
  fi
  printf '.'
  sleep 2
done
say ""

if [[ $READY -eq 0 ]]; then
  warn "$(t "Der Dienst hat in drei Minuten nicht geantwortet.
  Das kann am großen Modell liegen. Protokoll ansehen mit:
    ${COMPOSE[*]} logs --follow app" \
            "The service did not answer within three minutes.
  The large model may be the reason. View the log with:
    ${COMPOSE[*]} logs --follow app")"
  exit 1
fi

HEALTH_JSON=$(curl --fail --silent "${BASE_URL}/health" || echo '{}')
say ""
ok "$(t 'Der Konformitätshelfer läuft.' 'The AI Act Compliance Helper is running.')"
say ""
printf '   %-18s%s%s/%s\n' "$(t 'Oberfläche:' 'Interface:')" "$BOLD" "$BASE_URL" "$RESET"
printf '   %-18s%s/health\n' "$(t 'Zustandsbericht:' 'Health report:')" "$BASE_URL"
printf '   %-18s%s/openapi.json\n' "$(t 'Schnittstelle:' 'API:')" "$BASE_URL"
say ""
printf '%s\n' "$HEALTH_JSON" | python3 -c '
import json,sys
labels = {
    "de": ("Rechtsstellen:", "Suche mit:", "Formulierung:", "Hinweis:"),
    "en": ("Legal units:", "Search with:", "Wording:", "Note:"),
}[sys.argv[1]]
try: health=json.load(sys.stdin)
except Exception: sys.exit(0)
print("   %-18s%s" % (labels[0], health.get("units","?")))
print("   %-18s%s" % (labels[1], health.get("embedding_model","?")))
print("   %-18s%s" % (labels[2], health.get("llm","?")))
for warning in health.get("warnings",[]):
    print("   %-18s%s" % (labels[3], warning))
' "$UI_LANG" 2>/dev/null || true
say ""
say "$(t 'Anhalten mit:  ./scripts/start.sh --stopp' 'Stop with:  ./scripts/start.sh --stop')"
