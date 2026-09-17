import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Node parameter priority (highest first):
#   1. command line `name:=value` (any parameter listed in the params file)
#   2. params file (params_file argument, default config/params.yaml)
#   3. NODE_ARG_DEFAULTS below
#   4. declare_parameter defaults inside orb_tracker_node
# Node-parameter launch arguments default to "" meaning "not given on the command line",
# so they never override the params file.
NODE_ARG_DEFAULTS = {
    "target_image_path": "target.png",
    "world_frame": "map",
    "debug.enable": "true",
    "debug.img": "false",
}

ARGUMENTS = [
    DeclareLaunchArgument(
        "params_file",
        default_value=os.path.join(get_package_share_directory('object_tracker'), 'config', 'params.yaml'),
        description="Node parameter file",
    ),

    # Basic arguments (node parameters)
    DeclareLaunchArgument(
        "target_image_path",
        default_value="",
        description="Target image: absolute path, or file name under share/object_tracker/targets "
                    "(empty = params file, else 'target.png')",
    ),
    DeclareLaunchArgument(
        "world_frame",
        default_value="",
        description="Output frame; the robot TF tree must connect it to camera_link. Use camera_link for bench tests "
                    "(empty = params file, else 'map')",
    ),

    # RealSense camera
    DeclareLaunchArgument(
        "launch_camera",
        default_value="true",
        description="Also launch realsense2_camera (D405) with aligned depth",
    ),
    DeclareLaunchArgument(
        "camera_profile",
        default_value="848,480,30",
        description="D405 color and depth profile (width,height,fps); keep both at the same fps for sync",
    ),

    # Static camera TF (world_frame -> camera_link)
    # The robot normally publishes this; enable only for standalone tests.
    DeclareLaunchArgument(
        "cam_tf.enable",
        default_value="false",
        description="Publish static TF from world_frame to cam_tf.child_frame (only if the robot does not)",
    ),
    DeclareLaunchArgument(
        "cam_tf.child_frame",
        default_value="camera_link",
        description="Root frame of the RealSense TF tree",
    ),
    DeclareLaunchArgument("cam_tf.x", default_value="0.0", description="Camera X in world frame (m)"),
    DeclareLaunchArgument("cam_tf.y", default_value="0.0", description="Camera Y in world frame (m)"),
    DeclareLaunchArgument("cam_tf.z", default_value="0.0", description="Camera Z in world frame (m)"),
    DeclareLaunchArgument("cam_tf.roll", default_value="0.0", description="Camera roll (rad)"),
    DeclareLaunchArgument("cam_tf.pitch", default_value="0.0", description="Camera pitch (rad)"),
    DeclareLaunchArgument("cam_tf.yaw", default_value="0.0", description="Camera yaw (rad)"),

    # Debug arguments (node parameters)
    DeclareLaunchArgument(
        "debug.enable",
        default_value="",
        description="Enable debug log and tracked_object TF (empty = params file, else true)",
    ),
    DeclareLaunchArgument(
        "debug.img",
        default_value="",
        description="Enable image show for debugging (empty = params file, else false)",
    ),
]


def load_node_params(path):
    """Return the ros__parameters of the params file (all node sections merged)."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or {}
    params = {}
    for section in data.values():
        if isinstance(section, dict):
            params.update(section.get('ros__parameters', {}))
    return params


def parse_value(text, reference=None):
    """Parse a command-line string like YAML; follow the params file type so 100 stays a double."""
    value = yaml.safe_load(text)
    if isinstance(reference, float) and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if isinstance(reference, str) and not isinstance(value, str):
        return text
    return value


def launch_setup(context):
    params_file = LaunchConfiguration("params_file").perform(context)
    file_params = load_node_params(params_file)

    # layer 3: launch defaults, only for keys the params file does not set
    launch_defaults = {k: parse_value(v) for k, v in NODE_ARG_DEFAULTS.items()}

    # layer 1: command-line values; declared node arguments are "" unless given, other node
    # parameters only exist in the launch configurations when passed on the command line
    overrides = {}
    for key in set(file_params) | set(NODE_ARG_DEFAULTS):
        text = context.launch_configurations.get(key, "")
        if text != "":
            overrides[key] = parse_value(text, file_params.get(key))

    # same priority for the frame used by the static TF
    world_frame = str(overrides.get("world_frame", file_params.get("world_frame", launch_defaults["world_frame"])))

    orb_tracker_node = Node(
        package='object_tracker',
        executable='orb_tracker_node',
        name='orb_tracker_node',
        output='screen',
        parameters=[launch_defaults, params_file, overrides],
    )

    camera_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_static_tf',
        output='screen',
        condition=IfCondition(LaunchConfiguration("cam_tf.enable")),
        arguments=[
            '--x', LaunchConfiguration("cam_tf.x"),
            '--y', LaunchConfiguration("cam_tf.y"),
            '--z', LaunchConfiguration("cam_tf.z"),
            '--roll', LaunchConfiguration("cam_tf.roll"),
            '--pitch', LaunchConfiguration("cam_tf.pitch"),
            '--yaw', LaunchConfiguration("cam_tf.yaw"),
            '--frame-id', world_frame,
            '--child-frame-id', LaunchConfiguration("cam_tf.child_frame"),
        ],
    )

    return [camera_static_tf, orb_tracker_node]


def generate_launch_description():
    realsense = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('realsense2_camera'), 'launch', 'rs_launch.py')
        ),
        condition=IfCondition(LaunchConfiguration("launch_camera")),
        launch_arguments={
            'align_depth.enable': 'true',
            'enable_sync': 'true',
            # D405 has no RGB module: color is configured on the depth module
            'depth_module.color_profile': LaunchConfiguration("camera_profile"),
            'depth_module.depth_profile': LaunchConfiguration("camera_profile"),
        }.items(),
    )

    ld = LaunchDescription(ARGUMENTS)

    ld.add_action(realsense)
    ld.add_action(OpaqueFunction(function=launch_setup))

    return ld
