#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
The standalone updater is retired and read-only.
It cannot apply, restore, or copy the retired project architecture distribution.

Supported path:
1. install or update the Personal AI Hub;
2. register, create, or migrate the project through Hub workflows;
3. keep project task memory and optional knowledge in the project repository.

For Hub updates use scripts/update-installed-hub.sh with an explicit preview.
EOF
exit 2
