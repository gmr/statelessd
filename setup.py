import os
from distutils.core import setup

# Build the path to install the templates, example config and static files
base_path = '/usr/local/share/statelessd'
data_files = dict()
data_paths = ['static', 'templates', 'etc', 'examples']
for data_path in data_paths:
    for dir_path, dir_names, file_names in os.walk(data_path):
        install_path = '%s/%s' % (base_path, dir_path)
        if install_path not in data_files:
            data_files[install_path] = list()
        for file_name in file_names:
            data_files[install_path].append('%s/%s' % (dir_path, file_name))
with open('MANIFEST.in', 'w') as handle:
    for path in data_files:
        for filename in data_files[path]:
            handle.write('include %s\n' % filename)

setup(name='statelessd',
      version='0.0.5',
      description='Stateless HTTP -> AMQP gateway',
      url='http://github.com/gmr/statelessd',
      packages=['statelessd'],
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
      license='BSD',
      data_files=[(key, data_files[key]) for key in data_files.keys()],
      zip_safe=True,
      install_requires=['tinman', 'pika'])
