from setuptools import setup
from glob import glob
setup(name='drive_limits', version='0.0.1', packages=['drive_limits'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/drive_limits']),
                  ('share/drive_limits', ['package.xml'])],
      extras_require={'test': ['pytest']},
      entry_points={'console_scripts': ['scan-watch = scan_watch.node:main']} if 'drive_limits' == 'scan_watch' else {})
