from setuptools import setup
from glob import glob
setup(name='scan_watch_v3', version='0.0.1', packages=['scan_watch_v3'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/scan_watch_v3']),
                  ('share/scan_watch_v3', ['package.xml']),
                  ('share/scan_watch_v3/launch', glob('launch/*.launch.py')),
                  ('share/scan_watch_v3/config', glob('config/*.yaml'))],
      entry_points={'console_scripts': ['scan-watch = scan_watch_v3.node:main']})
