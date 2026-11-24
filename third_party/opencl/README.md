# OpenCL headers

The `CL/` headers are from the Khronos Group's
[OpenCL-Headers](https://github.com/KhronosGroup/OpenCL-Headers) repository, used here
only to compile Nexarch's optional OpenCL backend. They are licensed under the Apache
License 2.0; see `LICENSE` in this directory.

Nexarch loads the OpenCL ICD loader at runtime (`libOpenCL.so.1`, `OpenCL.dll`, or the
macOS OpenCL framework), so a CPU build and a GPU build both run on machines without an
OpenCL SDK installed. The loader and the vendor driver are not part of Nexarch.
