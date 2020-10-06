# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" This is all-in-one launch script intended for use by nav2 developers. """

import os

from ament_index_python.packages import get_package_prefix
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition
from nav2_common.launch import RewrittenYaml

from launch.launch_description_sources import PythonLaunchDescriptionSource


import launch.actions
import launch_ros.actions


def generate_launch_description():
    # Get the launch directory
    launch_dir = os.path.join(get_package_share_directory('self_flow'), 'launch')

    # Create the launch configuration variables
    autostart = launch.substitutions.LaunchConfiguration('autostart')
    use_amcl = launch.substitutions.LaunchConfiguration('use_amcl', default='true')
    bt_xml_file = launch.substitutions.LaunchConfiguration('bt')
    map_yaml_file = launch.substitutions.LaunchConfiguration('map')
    params_file = launch.substitutions.LaunchConfiguration('params')
    rviz_config_file = launch.substitutions.LaunchConfiguration('rviz_config')
    simulator = launch.substitutions.LaunchConfiguration('simulator')
    use_sim_time = launch.substitutions.LaunchConfiguration('use_sim_time')
    use_simulation = launch.substitutions.LaunchConfiguration('use_simulation')

    namespace = launch.substitutions.LaunchConfiguration('namespace')

    # Create our own temporary YAML files that include the following parameter substitutions
    param_substitutions = {
        'autostart': autostart,
        'bt_xml_filename': bt_xml_file,
        'use_sim_time': use_sim_time,
        'yaml_filename': map_yaml_file
    }
    configured_params = RewrittenYaml(
        source_file=params_file, rewrites=param_substitutions, convert_types=True)

    # Declare the launch arguments
    declare_autostart_cmd = launch.actions.DeclareLaunchArgument(
        'autostart',
        default_value='false',  #AUTOSTART
        description='Automatically startup the nav2 stack')

    declare_bt_xml_cmd = launch.actions.DeclareLaunchArgument(
        'bt',
        default_value=os.path.join(
            get_package_prefix('nav2_bt_navigator'),
            'behavior_trees/navigate_w_replanning_and_recovery.xml'),
        description='Full path to the Behavior Tree XML file to use for the BT navigator')

    declare_map_yaml_cmd = launch.actions.DeclareLaunchArgument(
        'map',
        default_value= os.path.join(get_package_share_directory('self_flow'), 'maps/house.yaml'),
        description='Full path to map file to load')

    declare_params_file_cmd = launch.actions.DeclareLaunchArgument(
        'params',
        default_value=[launch.substitutions.ThisLaunchFileDir(), '/nav2_params.yaml'],
        description='Full path to the ROS2 parameters file to use for all launched nodes')

    declare_rviz_config_file_cmd = launch.actions.DeclareLaunchArgument(
        'rviz_config',
        default_value= os.path.join(get_package_share_directory('self_flow'), 'rviz/nav2_default_view.rviz'),
        description='Full path to the RVIZ config file to use')

    declare_simulator_cmd = launch.actions.DeclareLaunchArgument(
        'simulator',
        default_value='gazebo',
        description='The simulator to use (gazebo or gzserver)')

    declare_use_sim_time_cmd = launch.actions.DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')

    declare_use_simulation_cmd = launch.actions.DeclareLaunchArgument(
        'use_simulation',
        default_value='True',
        description='Whether to run in simulation')


    declare_namespace_cmd = launch.actions.DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Namespace')



    stdout_linebuf_envvar = launch.actions.SetEnvironmentVariable(
        'RCUTILS_CONSOLE_STDOUT_LINE_BUFFERED', '1')

    # Specify the actions

    start_robot_cmd = launch.actions.IncludeLaunchDescription(
            PythonLaunchDescriptionSource([launch_dir, '/turtlebot3_agent.launch.py']), #change in case of namespace
            launch_arguments={'use_sim_time': use_sim_time}.items())


    start_rviz_cmd = launch.actions.ExecuteProcess(
        cmd=[os.path.join(get_package_prefix('rviz2'), 'lib/rviz2/rviz2'),
            ['-d', rviz_config_file]],
        cwd=[launch_dir], output='screen')

    exit_event_handler = launch.actions.RegisterEventHandler(
        event_handler=launch.event_handlers.OnProcessExit(
            target_action=start_rviz_cmd,
            on_exit=launch.actions.EmitEvent(event=launch.events.Shutdown(reason='rviz exited'))))


    start_map_server_cmd = launch_ros.actions.Node(
        package='nav2_map_server',
        node_executable='map_server',
        node_name='map_server',
        output='screen',
        parameters=[configured_params])


    start_localizer_cmd = launch_ros.actions.Node(
        package='nav2_amcl',
        node_executable='amcl',
        node_name='amcl',
	node_namespace= namespace,
        output='screen',
        parameters=[configured_params])


    start_world_model_cmd = launch_ros.actions.Node(
        package='nav2_world_model',
        node_executable='world_model',
	#node_namespace= namespace, 
        output='screen',
        parameters=[configured_params])


    start_dwb_cmd = launch_ros.actions.Node(
        package='dwb_controller',
        node_executable='dwb_controller',
	node_namespace= namespace,
        output='screen',
        parameters=[configured_params])


    start_planner_cmd = launch_ros.actions.Node(
        package='nav2_navfn_planner',
        node_executable='navfn_planner',
        node_name='navfn_planner',
	node_namespace= namespace,
        output='screen',
        parameters=[configured_params])


    start_navigator_cmd = launch_ros.actions.Node(
        package='nav2_bt_navigator',
        node_executable='bt_navigator',
        node_name='bt_navigator',
	node_namespace= namespace,
        output='screen',
        parameters=[configured_params])

    start_recovery_cmd = launch_ros.actions.Node(
        package='nav2_recoveries',
        node_executable='recoveries_node',
        node_name='recoveries',
	node_namespace= namespace,
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}])


    start_lifecycle_manager_cmd = launch.actions.ExecuteProcess(
        cmd=[
            os.path.join(
                get_package_prefix('nav2_lifecycle_manager'),
                'lib/nav2_lifecycle_manager/lifecycle_manager'),
            ['__params:=', configured_params]],
        cwd=[launch_dir], output='screen')

    # Create the launch description and populate
    ld = launch.LaunchDescription()

    # Declare the launch options
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_bt_xml_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_simulator_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_simulation_cmd)
    ld.add_action(declare_namespace_cmd)

    # Set environment variables
    ld.add_action(stdout_linebuf_envvar)

    # Add any actions to launch in simulation (conditioned on 'use_simulation')
    ld.add_action(start_robot_cmd)

    # Add other nodes and processes we need
    ld.add_action(start_rviz_cmd)
    ld.add_action(exit_event_handler)

    # Add the actions to launch all of the navigation nodes
    ld.add_action(start_lifecycle_manager_cmd)
 
#    if use_amcl=='true':
    ld.add_action(start_map_server_cmd)
    ld.add_action(start_localizer_cmd)
    
    ld.add_action(start_world_model_cmd)
    ld.add_action(start_dwb_cmd)
    ld.add_action(start_planner_cmd)
    ld.add_action(start_navigator_cmd)
    ld.add_action(start_recovery_cmd)

    return ld