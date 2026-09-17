cmake_minimum_required(VERSION 3.8)
project(object_tracker)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(message_filters REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS core imgproc features2d calib3d video highgui imgcodecs)

include_directories(
  ${OpenCV_INCLUDE_DIRS}
)

add_executable(orb_tracker_node
  src/orb_tracker_node.cpp
)

ament_target_dependencies(orb_tracker_node
  rclcpp
  sensor_msgs
  geometry_msgs
  cv_bridge
  message_filters
  tf2
  tf2_ros
  tf2_geometry_msgs
  ament_index_cpp
)

target_link_libraries(orb_tracker_node
  ${OpenCV_LIBRARIES}
)

add_executable(frame_capture_node
  src/frame_capture_node.cpp
)

ament_target_dependencies(frame_capture_node
  rclcpp
  sensor_msgs
  cv_bridge
)

target_link_libraries(frame_capture_node
  ${OpenCV_LIBRARIES}
)

install(TARGETS
  orb_tracker_node
  frame_capture_node
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch, config and target images
install(DIRECTORY launch config targets
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
