try:
    from setuptools import setup
    from setuptools.command.install import install as _install
    from setuptools.command.sdist import sdist as _sdist
except ImportError:
    from distutils.core import setup
    from distutils.command.install import install as _install
    from distutils.command.sdist import sdist as _sdist

class install(_install):
    def run(self):
        _install.run(self)

class sdist(_sdist):
    def make_release_tree(self, basedir, files):
        _sdist.make_release_tree(self, basedir, files)

setup(
    # metadata
    name='pyc-fmtstr-parser',
    description='Parser for printf/scanf format strings',
    long_description="""
        A nearly-complete parser for C printf/scanf format strings.
    """,
    license='LGPL2',
    version='1.0',
    author='Mark Laws',
    maintainer='Mark Laws',
    author_email='mdl@60hz.org',
    url='https://github.com/drvink/pyc-fmtstr-parser',
    platforms='Cross Platform',
    classifiers = [
        'Programming Language :: Python :: 2'],
    packages=['pyc_fmtstr_parser'],
    cmdclass={'install': install, 'sdist': sdist},
)
