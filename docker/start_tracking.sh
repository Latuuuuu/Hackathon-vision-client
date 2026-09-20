#!/bin/bash
# Container entry point used by docker compose: build if needed, then start the tracker.
#
# Environment (all optional, set them in compose.yaml or in docker/.env):
#   AUTOSTART=0            keep the old behaviour: just an idle shell, launch by hand
#   AUTO_BUILD=1           always colcon build before launching (default: only when install/ is missing)
#   LAUNCH_FILE=...        launch file in object_tracker (default: mask_tracker_vlm_bringup.launch.py)
#   LAUNCH_ARGS="a:=b ..." extra launch arguments (default: debug.img:=true)
set -o pipefail

WS="${ROS_WORKSPACE:-/home/vision/vision_ws}"
AUTOSTART="${AUTOSTART:-1}"
AUTO_BUILD="${AUTO_BUILD:-0}"
LAUNCH_FILE="${LAUNCH_FILE:-mask_tracker_vlm_bringup.launch.py}"
LAUNCH_ARGS="${LAUNCH_ARGS:-debug.img:=true}"

source /opt/ros/humble/setup.bash
cd "$WS" || exit 1

if [ "$AUTOSTART" != "1" ]; then
    echo "AUTOSTART=$AUTOSTART: not launching. Use 'docker exec -it <container> bash'."
    exec sleep infinity
fi

# A fresh clone has no install/ yet, so the first start builds the whole workspace (takes a while).
if [ "$AUTO_BUILD" = "1" ] || [ ! -f "$WS/install/setup.bash" ]; then
    echo "Building the workspace (AUTO_BUILD=$AUTO_BUILD)..."
    if ! colcon build --symlink-install; then
        echo "colcon build failed; staying up so you can debug with 'docker exec -it <container> bash'." >&2
        exec sleep infinity
    fi
fi

source "$WS/install/setup.bash"

echo "Launching: ros2 launch object_tracker $LAUNCH_FILE $LAUNCH_ARGS"
# exec: ros2 launch becomes PID 1, so 'docker compose stop' sends SIGTERM straight to it and the nodes shut down
exec ros2 launch object_tracker "$LAUNCH_FILE" $LAUNCH_ARGS
