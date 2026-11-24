#include "nnue.h"

#include <atomic>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#if defined(NEXARCH_OPENCL)

#define CL_TARGET_OPENCL_VERSION 120
#include <CL/cl.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace {

constexpr int KERNEL_WORKERS = 256;

struct Api {
  cl_int (*GetPlatformIDs)(cl_uint, cl_platform_id*, cl_uint*) = nullptr;
  cl_int (*GetDeviceIDs)(cl_platform_id, cl_device_type, cl_uint, cl_device_id*, cl_uint*) = nullptr;
  cl_int (*GetDeviceInfo)(cl_device_id, cl_device_info, size_t, void*, size_t*) = nullptr;
  cl_context (*CreateContext)(const cl_context_properties*, cl_uint, const cl_device_id*,
                              void (*)(const char*, const void*, size_t, void*), void*, cl_int*) = nullptr;
  cl_command_queue (*CreateCommandQueue)(cl_context, cl_device_id, cl_command_queue_properties, cl_int*) = nullptr;
  cl_program (*CreateProgramWithSource)(cl_context, cl_uint, const char**, const size_t*, cl_int*) = nullptr;
  cl_int (*BuildProgram)(cl_program, cl_uint, const cl_device_id*, const char*,
                         void (*)(cl_program, void*), void*) = nullptr;
  cl_int (*GetProgramBuildInfo)(cl_program, cl_device_id, cl_program_build_info, size_t, void*, size_t*) = nullptr;
  cl_kernel (*CreateKernel)(cl_program, const char*, cl_int*) = nullptr;
  cl_int (*SetKernelArg)(cl_kernel, cl_uint, size_t, const void*) = nullptr;
  cl_mem (*CreateBuffer)(cl_context, cl_mem_flags, size_t, void*, cl_int*) = nullptr;
  cl_int (*EnqueueWriteBuffer)(cl_command_queue, cl_mem, cl_bool, size_t, size_t, const void*, cl_uint,
                               const cl_event*, cl_event*) = nullptr;
  cl_int (*EnqueueNDRangeKernel)(cl_command_queue, cl_kernel, cl_uint, const size_t*, const size_t*,
                                 const size_t*, cl_uint, const cl_event*, cl_event*) = nullptr;
  cl_int (*EnqueueReadBuffer)(cl_command_queue, cl_mem, cl_bool, size_t, size_t, void*, cl_uint,
                              const cl_event*, cl_event*) = nullptr;
  cl_int (*Finish)(cl_command_queue) = nullptr;
  cl_int (*ReleaseMemObject)(cl_mem) = nullptr;
  cl_int (*ReleaseKernel)(cl_kernel) = nullptr;
  cl_int (*ReleaseProgram)(cl_program) = nullptr;
  cl_int (*ReleaseCommandQueue)(cl_command_queue) = nullptr;
  cl_int (*ReleaseContext)(cl_context) = nullptr;
};

struct Gpu {
  std::mutex lock;
  Api api;
  bool loaded = false;
  bool ready = false;
  cl_platform_id platform = nullptr;
  cl_device_id device = nullptr;
  cl_context context = nullptr;
  cl_command_queue queue = nullptr;
  cl_program program = nullptr;
  cl_kernel kernel = nullptr;
  cl_mem weights = nullptr;
  cl_mem input = nullptr;
  cl_mem output = nullptr;
  int hidden = 0;
  std::string path;
  std::string device_name;
};

Gpu& gpu() {
  static Gpu g;
  return g;
}

std::atomic<bool> use_gpu{false};

const char* KERNEL = R"CLC(
__kernel void eval(__global const short* a, __global const short* w, const int h, __global long* out) {
  const int gid = (int)get_global_id(0);
  const int total = 2 * h;
  long sum = 0;
  for (int i = gid; i < total; i += 256) {
    int x = (int)a[i];
    x = x < 0 ? 0 : (x > 255 ? 255 : x);
    sum += (long)x * (long)w[i] * (long)x;
  }
  __local long partial[256];
  partial[gid] = sum;
  barrier(CLK_LOCAL_MEM_FENCE);
  for (int stride = 128; stride > 0; stride >>= 1) {
    if (gid < stride) partial[gid] += partial[gid + stride];
    barrier(CLK_LOCAL_MEM_FENCE);
  }
  if (gid == 0) out[0] = partial[0];
}
)CLC";

template <typename T>
bool load(void* lib, const char* name, T& fn) {
#if defined(_WIN32)
  fn = reinterpret_cast<T>(GetProcAddress(reinterpret_cast<HMODULE>(lib), name));
#else
  fn = reinterpret_cast<T>(dlsym(lib, name));
#endif
  return fn != nullptr;
}

void* open_library() {
#if defined(_WIN32)
  return reinterpret_cast<void*>(LoadLibraryA("OpenCL.dll"));
#elif defined(__APPLE__)
  void* h = dlopen("/System/Library/Frameworks/OpenCL.framework/OpenCL", RTLD_LAZY);
  return h ? h : dlopen("libOpenCL.dylib", RTLD_LAZY);
#else
  void* h = dlopen("libOpenCL.so.1", RTLD_LAZY);
  return h ? h : dlopen("libOpenCL.so", RTLD_LAZY);
#endif
}

bool load_api(Api& a) {
  void* lib = open_library();
  if (!lib) return false;
  return load(lib, "clGetPlatformIDs", a.GetPlatformIDs) &&
         load(lib, "clGetDeviceIDs", a.GetDeviceIDs) &&
         load(lib, "clGetDeviceInfo", a.GetDeviceInfo) &&
         load(lib, "clCreateContext", a.CreateContext) &&
         load(lib, "clCreateCommandQueue", a.CreateCommandQueue) &&
         load(lib, "clCreateProgramWithSource", a.CreateProgramWithSource) &&
         load(lib, "clBuildProgram", a.BuildProgram) &&
         load(lib, "clGetProgramBuildInfo", a.GetProgramBuildInfo) &&
         load(lib, "clCreateKernel", a.CreateKernel) &&
         load(lib, "clSetKernelArg", a.SetKernelArg) &&
         load(lib, "clCreateBuffer", a.CreateBuffer) &&
         load(lib, "clEnqueueWriteBuffer", a.EnqueueWriteBuffer) &&
         load(lib, "clEnqueueNDRangeKernel", a.EnqueueNDRangeKernel) &&
         load(lib, "clEnqueueReadBuffer", a.EnqueueReadBuffer) &&
         load(lib, "clFinish", a.Finish) &&
         load(lib, "clReleaseMemObject", a.ReleaseMemObject) &&
         load(lib, "clReleaseKernel", a.ReleaseKernel) &&
         load(lib, "clReleaseProgram", a.ReleaseProgram) &&
         load(lib, "clReleaseCommandQueue", a.ReleaseCommandQueue) &&
         load(lib, "clReleaseContext", a.ReleaseContext);
}

void release(Gpu& g) {
  if (g.api.ReleaseMemObject) {
    if (g.weights) g.api.ReleaseMemObject(g.weights);
    if (g.input) g.api.ReleaseMemObject(g.input);
    if (g.output) g.api.ReleaseMemObject(g.output);
  }
  if (g.kernel) g.api.ReleaseKernel(g.kernel);
  if (g.program) g.api.ReleaseProgram(g.program);
  if (g.queue) g.api.ReleaseCommandQueue(g.queue);
  if (g.context) g.api.ReleaseContext(g.context);
  g.weights = g.input = g.output = nullptr;
  g.kernel = nullptr;
  g.program = nullptr;
  g.queue = nullptr;
  g.context = nullptr;
  g.ready = false;
  g.hidden = 0;
  g.path.clear();
}

}  // namespace

namespace nnue {

void set_gpu(bool on) { use_gpu.store(on, std::memory_order_relaxed); }
bool gpu_enabled() { return use_gpu.load(std::memory_order_relaxed); }

bool gpu_init(const Network& net, int device_index, std::string& error) {
  Gpu& g = gpu();
  std::lock_guard<std::mutex> guard(g.lock);
  release(g);
  if (!g.loaded) {
    g.loaded = load_api(g.api);
    if (!g.loaded) {
      error = "OpenCL loader not found";
      return false;
    }
  }
  cl_uint count = 0;
  if (g.api.GetPlatformIDs(0, nullptr, &count) != CL_SUCCESS || count == 0) {
    error = "no OpenCL platform";
    return false;
  }
  std::vector<cl_platform_id> platforms(count);
  g.api.GetPlatformIDs(count, platforms.data(), nullptr);
  int seen = 0;
  for (cl_platform_id p : platforms) {
    cl_uint n = 0;
    if (g.api.GetDeviceIDs(p, CL_DEVICE_TYPE_GPU, 0, nullptr, &n) != CL_SUCCESS || n == 0) continue;
    std::vector<cl_device_id> devices(n);
    if (g.api.GetDeviceIDs(p, CL_DEVICE_TYPE_GPU, n, devices.data(), nullptr) != CL_SUCCESS) continue;
    for (cl_device_id d : devices) {
      if (seen++ == device_index) {
        g.platform = p;
        g.device = d;
        break;
      }
    }
    if (g.device) break;
  }
  if (!g.device) {
    error = "no OpenCL GPU " + std::to_string(device_index);
    return false;
  }
  char name[256] = {};
  g.api.GetDeviceInfo(g.device, CL_DEVICE_NAME, sizeof(name), name, nullptr);
  g.device_name = name;
  cl_int rc = CL_SUCCESS;
  g.context = g.api.CreateContext(nullptr, 1, &g.device, nullptr, nullptr, &rc);
  if (!g.context || rc != CL_SUCCESS) {
    error = "cannot create an OpenCL context";
    release(g);
    return false;
  }
  g.queue = g.api.CreateCommandQueue(g.context, g.device, 0, &rc);
  if (!g.queue || rc != CL_SUCCESS) {
    error = "cannot create an OpenCL queue";
    release(g);
    return false;
  }
  const char* source = KERNEL;
  g.program = g.api.CreateProgramWithSource(g.context, 1, &source, nullptr, &rc);
  if (!g.program || rc != CL_SUCCESS) {
    error = "cannot create the OpenCL program";
    release(g);
    return false;
  }
  rc = g.api.BuildProgram(g.program, 1, &g.device, "", nullptr, nullptr);
  if (rc != CL_SUCCESS) {
    size_t size = 0;
    g.api.GetProgramBuildInfo(g.program, g.device, CL_PROGRAM_BUILD_LOG, 0, nullptr, &size);
    std::vector<char> log(size + 1);
    g.api.GetProgramBuildInfo(g.program, g.device, CL_PROGRAM_BUILD_LOG, size, log.data(), nullptr);
    error = std::string("OpenCL build failed: ") + log.data();
    release(g);
    return false;
  }
  g.kernel = g.api.CreateKernel(g.program, "eval", &rc);
  if (!g.kernel || rc != CL_SUCCESS) {
    error = "cannot create the OpenCL kernel";
    release(g);
    return false;
  }
  g.weights = g.api.CreateBuffer(g.context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR,
                                 net.out_weights.size() * sizeof(i16), const_cast<i16*>(net.out_weights.data()), &rc);
  g.input = g.api.CreateBuffer(g.context, CL_MEM_READ_ONLY, size_t(2) * net.hidden * sizeof(i16), nullptr, &rc);
  g.output = g.api.CreateBuffer(g.context, CL_MEM_WRITE_ONLY, sizeof(cl_long), nullptr, &rc);
  if (!g.weights || !g.input || !g.output || rc != CL_SUCCESS) {
    error = "cannot allocate OpenCL buffers";
    release(g);
    return false;
  }
  const cl_int hidden = net.hidden;
  const cl_int ok = g.api.SetKernelArg(g.kernel, 0, sizeof(cl_mem), &g.input) |
                    g.api.SetKernelArg(g.kernel, 1, sizeof(cl_mem), &g.weights) |
                    g.api.SetKernelArg(g.kernel, 2, sizeof(cl_int), &hidden) |
                    g.api.SetKernelArg(g.kernel, 3, sizeof(cl_mem), &g.output);
  if (ok != CL_SUCCESS) {
    error = "cannot set the OpenCL kernel arguments";
    release(g);
    return false;
  }
  g.hidden = net.hidden;
  g.path = net.path;
  g.ready = true;
  return true;
}

void gpu_shutdown() {
  Gpu& g = gpu();
  std::lock_guard<std::mutex> guard(g.lock);
  release(g);
}

bool gpu_ready() {
  Gpu& g = gpu();
  std::lock_guard<std::mutex> guard(g.lock);
  return g.ready;
}

std::string gpu_info() {
  Gpu& g = gpu();
  std::lock_guard<std::mutex> guard(g.lock);
  return g.ready ? g.device_name : std::string();
}

int evaluate_gpu(const Network& net, const Accumulator& acc, int stm) {
  Gpu& g = gpu();
  std::lock_guard<std::mutex> guard(g.lock);
  if (!g.ready || g.hidden != net.hidden || g.path != net.path) return GPU_FAIL;
  const int h = net.hidden;
  thread_local std::vector<i16> input;
  input.resize(size_t(2) * h);
  std::memcpy(input.data(), acc.v[stm], size_t(h) * sizeof(i16));
  std::memcpy(input.data() + h, acc.v[stm ^ 1], size_t(h) * sizeof(i16));
  const size_t bytes = input.size() * sizeof(i16);
  if (g.api.EnqueueWriteBuffer(g.queue, g.input, CL_TRUE, 0, bytes, input.data(), 0, nullptr, nullptr) != CL_SUCCESS) {
    g.ready = false;
    return GPU_FAIL;
  }
  const size_t workers = KERNEL_WORKERS;
  if (g.api.EnqueueNDRangeKernel(g.queue, g.kernel, 1, nullptr, &workers, &workers, 0, nullptr, nullptr) != CL_SUCCESS) {
    g.ready = false;
    return GPU_FAIL;
  }
  cl_long raw = 0;
  if (g.api.EnqueueReadBuffer(g.queue, g.output, CL_TRUE, 0, sizeof(raw), &raw, 0, nullptr, nullptr) != CL_SUCCESS) {
    g.ready = false;
    return GPU_FAIL;
  }
  i64 sum = i64(raw);
  sum /= QA;
  sum += net.out_bias;
  return int(sum * SCALE / (QA * QB));
}

}  // namespace nnue

#else

namespace nnue {

void set_gpu(bool) {}
bool gpu_enabled() { return false; }
bool gpu_init(const Network&, int, std::string& error) {
  error = "built without OpenCL";
  return false;
}
void gpu_shutdown() {}
bool gpu_ready() { return false; }
std::string gpu_info() { return {}; }
int evaluate_gpu(const Network&, const Accumulator&, int) { return GPU_FAIL; }

}  // namespace nnue

#endif
