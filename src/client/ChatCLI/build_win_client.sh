docker run --rm -ti \
 --env-file <(env | grep -iE 'DEBUG|NODE_|ELECTRON_|YARN_|NPM_|CI|GH_|GITHUB_|BT_|AWS_|STRIP|BUILD_') \
 -v /$(pwd):/project \
 -v ~/.cache/electron:/root/.cache/electron \
 -v ~/.cache/electron-builder:/root/.cache/electron-builder \
 electronuserland/builder:wine \
 /bin/bash -c "npm install && npm run dist -- --win"