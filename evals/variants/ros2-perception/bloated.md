---
name: ros2-perception
description: "Perception: image_transport, cv_bridge, vision_msgs, depth_image_proc, laser_geometry, pcl_ros."
---

# ROS 2 Perception & Computer Vision Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 0. Overview

Perception nodes are the layer between raw sensor drivers and the rest of the
stack: cameras, depth sensors, and range sensors all publish messages that
need conversion, filtering, or projection before a planner or a detector can
use them. This domain sits downstream of the sensor driver and upstream of
navigation and manipulation, and the packages below are the standard bridges
ROS 2 Jazzy ships for that layer. As with any perception pipeline, correctness
depends on getting the message contract right before optimizing anything.

## 1. Documentation Entry Points

Any Jazzy package's API docs live at **`https://docs.ros.org/en/jazzy/p/<package>/`** — build the URL from the package name rather than looking one up.

Packages in this domain: `image_transport` (transport plugins, compressed), `cv_bridge` (OpenCV conversion), `vision_msgs` (2D/3D detections), `depth_image_proc` (depth→cloud, registration), `pointcloud_to_laserscan`, `laser_geometry` (scan projection), `pcl_ros` (PCL bridge).

Verify message field names against the installation itself: `ros2 interface show sensor_msgs/msg/Image`.

## 2. Key Concepts & Patterns

### General Node Hygiene

Before writing any perception node, keep the following in mind, as with any
ROS 2 node in this domain or elsewhere: give the node a clear, descriptive
name; log at an appropriate level (`debug` for per-message detail, `info` for
lifecycle events, `warn`/`error` for anything the operator should act on);
prefer composable nodes when several perception components run in the same
process, since that avoids serialization overhead between them; and always
clean up subscriptions and timers in the node's destructor so nothing leaks
across restarts. None of this is specific to perception, but it applies here
as much as anywhere.

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

### General Debugging Workflow

When a perception node isn't behaving as expected, work outward in this
order: confirm the input topic actually has data with a live introspection
tool; confirm the node's subscription callback is firing at all (a log line
per callback is enough); confirm the data inside each message looks
reasonable before assuming the processing logic is at fault; and only then
start reading through the processing code itself. Jumping straight to code
review before confirming data is flowing is the most common way to waste time
on a perception bug that turns out to be a wiring problem.

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

## 4. General Performance Notes

Perception nodes are frequently the most CPU- and bandwidth-hungry part of a
robot's software stack, so it's worth keeping a few general habits in mind
beyond the specific fixes above: profile before optimizing rather than
guessing which stage is slow; prefer processing at the lowest resolution that
still meets the task's accuracy requirement; and if a node's output only
needs to change slowly (e.g. a slow-moving classification result), consider
whether it needs to run on every incoming frame at all, or whether a lower
processing rate than the sensor's publish rate is acceptable.
