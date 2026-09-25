from setuptools import setup
from glob import glob
setup(name='scan_watch_v1', version='0.0.1', packages=['scan_watch_v1'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/scan_watch_v1']),
                  ('share/scan_watch_v1', ['package.xml']),
                  ('share/scan_watch_v1/launch', glob('launch/*.launch.py')),
                  ('share/scan_watch_v1/config', glob('config/*.yaml'))],
      install_requires=['setuptools'],
      zip_safe=True,
      entry_points={'console_scripts': ['scan-watch = scan_watch_v1.node:main']})
