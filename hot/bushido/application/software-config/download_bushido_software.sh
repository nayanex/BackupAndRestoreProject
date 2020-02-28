#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="DOWNLOAD-BUSHIDO-SOFTWARE"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

# keystonerc exports

function get_token {
    curl --insecure -i -H "Content-Type: application/json" -d '
    { "auth": {
        "identity": {
          "methods": ["password"],
          "password": {
            "user": {
              "name": "'$OS_USERNAME'",
              "domain": { "id": "default" },
              "password": "'$OS_PASSWORD'"
            }
          }
        },
        "scope": {
          "project": {
            "name": "'$OS_PROJECT_NAME'",
            "domain": { "id": "default" }
          }
        }
      }
    }' "$OS_AUTH_URL/auth/tokens" 2>/dev/null  | awk '/X-Subject-Token/ {print $2}' | sed  's/\r//'
}
OS_TOKEN=$(get_token)

JEMALLOC_PATH=/v2/images/6a26269b-f9fa-4b21-909b-acaa654d89a2/file
BUSHIDO_PATH=/v2/images/5e8f1bfb-513a-4f50-96d9-3baccc43c126/file
curl --insecure -s -H "X-Auth-Token: $OS_TOKEN" https://10.2.63.251:13292/$JEMALLOC_PATH > /home/bushido/jemalloc.rpm
curl --insecure -s -H "X-Auth-Token: $OS_TOKEN"  https://10.2.63.251:13292/$BUSHIDO_PATH > /home/bushido/bushido.tar