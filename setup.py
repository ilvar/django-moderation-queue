from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='django-moderation-queue',
      version=version,
      description="Generic Django objects moderation application. With moderation queue!",

      classifiers=[
        'Development Status :: 1 - Initial',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
      ],
      keywords='django moderation models',
      author='Arcady Chumachenko',
      author_email='arcady.chumachenko@gmail.com',
      url='http://github.com/ilvar/django-moderation-queue',
      license='BSD',
      packages = find_packages('.'),
      package_dir = {'': '.'},
      include_package_data=True,
      install_requires=[
          'setuptools',
      ],
      zip_safe=False,
)
