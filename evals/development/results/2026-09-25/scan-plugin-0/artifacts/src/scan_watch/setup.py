from setuptools import setup
from glob import glob
setup(name='scan_watch', version='0.0.1', packages=['scan_watch'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/scan_watch']),
                  ('share/scan_watch', ['package.xml']),
                  ('share/scan_watch/launch', glob('launch/*.launch.py')),
                  ('share/scan_watch/config', glob('config/*.yaml'))],
      install_requires=['setuptools'],
      zip_safe=True,
      entry_points={'console_scripts': ['scan-watch = scan_watch.node:main']})
