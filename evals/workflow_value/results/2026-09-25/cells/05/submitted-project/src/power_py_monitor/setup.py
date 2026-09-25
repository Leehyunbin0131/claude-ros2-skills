from setuptools import setup

package_name = 'power_py_monitor'

setup(
    name=package_name,
    version='0.3.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Robot Team',
    maintainer_email='robot-team@example.com',
    description='Python power monitor.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'monitor = power_py_monitor.node:main',
        ],
    },
)
