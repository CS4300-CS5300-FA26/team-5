#!/usr/bin/env bash
# Smoke-tests the live site after the CI deploy job pushes to Heroku.
#
# `git push` to Heroku returns while the release command (migrations) is still
# running, and the old release keeps serving until it finishes. So this first
# waits until Heroku's current release is the commit we pushed, then checks
# that the site responds with the expected content.
#
# Needs: HEROKU_API_KEY, HEROKU_APP, APP_URL (no trailing slash), EXPECTED_SHA.
set -euo pipefail

: "${HEROKU_API_KEY:?}" "${HEROKU_APP:?}" "${APP_URL:?}" "${EXPECTED_SHA:?}"
RELEASE_TIMEOUT="${RELEASE_TIMEOUT:-600}"
SITE_TIMEOUT="${SITE_TIMEOUT:-120}"

heroku_api() {
  curl -sS --fail --max-time 30 \
    -H "Accept: application/vnd.heroku+json; version=3" \
    -H "Authorization: Bearer ${HEROKU_API_KEY}" \
    "$@"
}

json_field() {
  python3 -c 'import json, sys
data = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    data = data[key] if isinstance(data, dict) else data[int(key)]
print("" if data is None else data)' "$1"
}

# 1. Wait for the pushed commit to become the current release.
echo "Waiting for ${HEROKU_APP} to release ${EXPECTED_SHA}..."
deadline=$((SECONDS + RELEASE_TIMEOUT))
while :; do
  release="$(heroku_api -H "Range: version ..; order=desc, max=1" \
    "https://api.heroku.com/apps/${HEROKU_APP}/releases")"
  version="$(json_field 0.version <<<"$release")"
  status="$(json_field 0.status <<<"$release")"
  current="$(json_field 0.current <<<"$release")"
  slug_id="$(json_field 0.slug.id <<<"$release")"
  commit=""
  if [ -n "$slug_id" ]; then
    commit="$(heroku_api "https://api.heroku.com/apps/${HEROKU_APP}/slugs/${slug_id}" | json_field commit)"
  fi
  echo "  v${version}: status=${status} current=${current} commit=${commit:-none}"

  if [ "$commit" = "$EXPECTED_SHA" ]; then
    if [ "$status" = "failed" ]; then
      echo "::error::Heroku release v${version} failed. Check the release command output with: heroku releases:output ${version} -a ${HEROKU_APP}"
      exit 1
    fi
    if [ "$status" = "succeeded" ] && [ "$current" = "True" ]; then
      break
    fi
  fi
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "::error::Release of ${EXPECTED_SHA} did not become current within ${RELEASE_TIMEOUT}s (latest is v${version}, status ${status})."
    exit 1
  fi
  sleep 10
done
echo "Release v${version} is live."

# 2. Check the site. Retry while the dynos restart on the new release.
body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT
failure=""

# check PATH [TEXT]: PATH returns 200 and, if given, its body contains TEXT.
check() {
  local code
  code="$(curl -sS -o "$body_file" -w '%{http_code}' --max-time 30 "${APP_URL}$1" || true)"
  if [ "$code" != "200" ]; then
    failure="GET $1 returned HTTP ${code:-no response}"
    return 1
  fi
  if [ -n "${2:-}" ] && ! grep -qF "$2" "$body_file"; then
    failure="GET $1 returned 200 but did not contain \"$2\""
    return 1
  fi
  echo "  ok: GET $1"
}

run_checks() {
  check / "Binge and Bosses" || return 1
  local stylesheet
  stylesheet="$(grep -oE '/static/[^"]+\.css' "$body_file" | head -n 1 || true)"
  if [ -z "$stylesheet" ]; then
    failure="GET / has no stylesheet link under /static/"
    return 1
  fi
  check /accounts/login/ "Log" || return 1
  check /accounts/signup/ "Sign" || return 1
  check "$stylesheet" || return 1
}

echo "Smoke-testing ${APP_URL}..."
deadline=$((SECONDS + SITE_TIMEOUT))
until run_checks; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "::error::Production smoke test failed: ${failure}."
    echo "Last response body (first 40 lines):"
    head -n 40 "$body_file" || true
    exit 1
  fi
  echo "  retrying: ${failure}"
  sleep 10
done
echo "Production smoke test passed."
