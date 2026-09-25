from setuptools import setup
from glob import glob
setup(name='scan_watch_v2', version='0.0.1', packages=['scan_watch_v2'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/scan_watch_v2']),
                  ('share/scan_watch_v2', ['package.xml']),
                  ('share/scan_watch_v2/launch', glob('launch/*.launch.py')),
                  ('share/scan_watch_v2/config', glob('config/*.yaml'))],
      extras_require={'test': ['pytest']},
      entry_points={'console_scripts': ['scan-watch = scan_watch_v2.node:main']})
