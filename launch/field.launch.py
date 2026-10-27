import os

from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetLaunchConfiguration, IncludeLaunchDescription, SetEnvironmentVariable, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition


def generate_launch_description():

    # package paths
    sim_path = os.path.join(get_package_share_directory('rbe3002_sim'))
    tb3_gz_pkg = os.path.join(get_package_share_directory('turtlebot3_gazebo'), 'launch')
    gz_dir = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch')

    # secondary file paths for locating resources
    models_path = os.path.join(sim_path, 'models')
    worlds_path = os.path.join(sim_path, 'worlds')

    # gz sim resource path environment variable
    gz_sim_resource = SetEnvironmentVariable(
        name = 'GZ_SIM_RESOURCE_PATH',
        value=f"{models_path}:{worlds_path}:{sim_path}"
    )

    # arg to toggle what world is launched
    big_field = LaunchConfiguration('big')
    big_field_cmd = DeclareLaunchArgument(
        'big', 
        default_value='false', 
        description='true = big field world, false = small field world'
    )
    

    # settings for turtlebot spawn location and world name
    arguments = LaunchDescription([
        # big field args
        SetLaunchConfiguration('x_pose', '-1.65', condition=IfCondition(big_field)),
        SetLaunchConfiguration('y_pose', '0.95', condition=IfCondition(big_field)),
        SetLaunchConfiguration('world_name', 'big-field', condition=IfCondition(big_field)),

        # small field args
        SetLaunchConfiguration('x_pose', '0.15', condition=UnlessCondition(big_field)),
        SetLaunchConfiguration('y_pose', '0.0', condition=UnlessCondition(big_field)),
        SetLaunchConfiguration('world_name', 'small-field', condition=UnlessCondition(big_field))
    ])

    # actually run gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_dir, '/gz_sim.launch.py']),
        launch_arguments = [
            ('gz_args', [LaunchConfiguration('world_name'),'.sdf',' -v4',' -r']),
            ('use_sim_time', 'True')
        ]
    )

    # spawn in turtlebot
    spawn_turtlebot_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gz_pkg, 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': LaunchConfiguration('x_pose'),
            'y_pose': LaunchConfiguration('y_pose'),
            'use_sim_time': 'true'
        }.items()
    )

    # robot state publisher
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gz_pkg, 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )   

    # move the camera to a way better position in gazebo (yes, I tried using a config file instead of this)
    camera_small = ExecuteProcess(
        cmd=[
            'gz', 'service',
            '-s', '/gui/move_to/pose',
            '--reqtype', 'gz.msgs.GUICamera',
            '--reptype', 'gz.msgs.Boolean',
            '--req',
            'pose: { position: { x: 0.5, y: -1.0, z: 2.0 }, '
            'orientation: { x: 0, y: 1.0, z: 0.0, w: 1.0 } }'
        ],
        condition=UnlessCondition(big_field),
        output='log'
    )

    camera_big = ExecuteProcess(
        cmd=[
            'gz', 'service',
            '-s', '/gui/move_to/pose',
            '--reqtype', 'gz.msgs.GUICamera',
            '--reptype', 'gz.msgs.Boolean',
            '--req',
            'pose: { position: { x: -0.2, y: 0.0, z: 2.6 }, '
            'orientation: { x: 0, y: 1.0, z: 0.0, w: 1.0 } }'
        ],
        condition=IfCondition(big_field),
        output='log'
    )
  

    # slightly delay gui command
    delay_set_pose = TimerAction(
        period=1.0, 
        actions=[camera_big, camera_small]
    )

    return LaunchDescription([
        gz_sim_resource,
        big_field_cmd,
        arguments,
        gazebo,
        spawn_turtlebot_cmd,
        robot_state_publisher_cmd,
        delay_set_pose
    ])