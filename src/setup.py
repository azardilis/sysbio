from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
 
ext_modules = [Extension("abcinfer_multi_thr", ["abcinfer_multi_thr.py"])]
 
setup(
  name = 'ABC inference',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules
)
