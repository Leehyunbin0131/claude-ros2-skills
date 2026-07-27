---
name: ros2-perception
description: "Perception: image_transport, cv_bridge, vision_msgs, depth_image_proc, laser_geometry, pcl_ros."
---

# ROS 2 Perception & Computer Vision Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Documentation Entry Points

Any Jazzy package's API docs live at **`https://docs.ros.org/en/jazzy/p/<package>/`** — build the URL from the package name rather than looking one up.

Packages in this domain: `image_transport` (transport plugins, compressed), `cv_bridge` (OpenCV conversion), `vision_msgs` (2D/3D detections), `depth_image_proc` (depth→cloud, registration), `pointcloud_to_laserscan`, `laser_geometry` (scan projection), `pcl_ros` (PCL bridge).

Verify message field names against the installation itself: `ros2 interface show sensor_msgs/msg/Image`.

## 2. Key Concepts & Patterns

### `cv_bridge` OpenCV Conversion (C++)
```cpp
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/image_encodings.hpp>
#include <cv_bridge/cv_bridge.hpp>
#include <opencv2/imgproc/imgproc.hpp>

void process_image(const sensor_msgs::msg::Image::ConstSharedPtr & msg) {
  cv_bridge::CvImagePtr cv_ptr = cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::BGR8);
  cv::circle(cv_ptr->image, cv::Point(50, 50), 10, CV_RGB(255, 0, 0), 2);
  sensor_msgs::msg::Image::SharedPtr out_msg = cv_ptr->toImageMsg();
}
```

## 3. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Image topic listed but callback never fires | QoS mismatch: camera drivers publish BestEffort, subscriber defaults Reliable | Subscribe with sensor-data QoS — **C++ `rclcpp::SensorDataQoS()`, Python `rclpy.qos.qos_profile_sensor_data`** (there is no `rclcpp` module in Python); confirm with `ros2 topic info <topic> -v` |
| `cv_bridge` throws encoding exception | Requested encoding doesn't match source (`bgr8` vs `rgb8`, `16UC1` depth) | Use `toCvCopy(msg, msg->encoding)` (passthrough) or convert explicitly; never assume `bgr8` for depth |
| Depth values look 1000x off or all ~0 | `16UC1` is millimeters, `32FC1` is meters — unit confusion | Check `msg->encoding` before scaling; divide 16UC1 by 1000.0 for meters |
| Point cloud misaligned with the RGB image | Depth not registered into the color optical frame | Use the `depth_registered` topic or `depth_image_proc` register node; verify both `frame_id`s |
| `pointcloud_to_laserscan` outputs empty scans | `min_height`/`max_height` band excludes all points, or `target_frame` transform missing | Widen the height band around the sensor's actual Z; check TF to `target_frame` |
| Detection boxes drawn at wrong image positions | Processing the rectified topic but projecting with the raw camera matrix (or vice versa) | Pair `image_rect` with `P` (projection) matrix, raw `image` with `K`; don't mix |
| High CPU from image subscribers | Subscribing raw full-resolution images over the network | Use `image_transport` compressed transport, or throttle/downscale before processing |
