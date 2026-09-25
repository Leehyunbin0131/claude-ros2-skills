from setuptools import setup
from glob import glob
setup(name='drive_limits_v1', version='0.0.1', packages=['drive_limits_v1'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/drive_limits_v1']),
                  ('share/drive_limits_v1', ['package.xml'])],
      entry_points={'console_scripts': ['scan-watch = scan_watch_v1.node:main']} if 'drive_limits_v1' == 'scan_watch_v1' else {})
