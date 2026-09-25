cmake_minimum_required(VERSION 3.8)
project(range_cpp_monitor)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(range_interfaces REQUIRED)

add_library(${PROJECT_NAME}_conversion src/conversion.cpp)
target_include_directories(${PROJECT_NAME}_conversion PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>)
ament_target_dependencies(${PROJECT_NAME}_conversion range_interfaces)

add_executable(monitor src/monitor_node.cpp)
target_link_libraries(monitor ${PROJECT_NAME}_conversion)
ament_target_dependencies(monitor rclcpp std_msgs range_interfaces)

install(TARGETS monitor DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_conversion test/test_conversion.cpp)
  target_link_libraries(test_conversion ${PROJECT_NAME}_conversion)
  ament_target_dependencies(test_conversion range_interfaces)
endif()

ament_package()
