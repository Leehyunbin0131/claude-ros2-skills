# Contributing

- CI builds and tests every package from a clean checkout on Ubuntu 24.04 with
  only `/opt/ros/jazzy` sourced:

      colcon build
      colcon test --return-code-on-test-failure --python-testing pytest

  A change is ready when that passes from a clean checkout.
- Each behaviour change needs regression tests in every affected package. For
  conversion changes, cover both a valid and an invalid reading.
- Edit sources only. Do not hand-edit generated files or anything under
  `build/`, `install/` or `log/`.
- Keep the public conversion helpers, executables and topic names described
  in `README.md`.
- Interface changes need an entry at the top of `src/thermal_interfaces/CHANGELOG.rst`.
- Package versions are bumped at release time; do not change them in a
  feature change.
