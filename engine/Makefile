EXE ?= nexarch
ARCH ?= native
GPU ?= 0
CXXFLAGS ?= -O3 -std=c++20 -march=$(ARCH) -DNDEBUG -flto -pthread -Wall -Wextra
ifeq ($(GPU),1)
  CXXFLAGS += -DNEXARCH_OPENCL -I../third_party/opencl
  ifneq ($(shell uname -s),Darwin)
    LDFLAGS += -ldl
  endif
endif
SOURCES := $(wildcard src/*.cpp)
HEADERS := $(wildcard src/*.h)

$(EXE): $(SOURCES) $(HEADERS)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $@ $(LDFLAGS)

clean:
	rm -f $(EXE)

cpu:
	$(MAKE) GPU=0 ARCH=x86-64-v2 EXE=nexarch-cpu

cpu-avx2:
	$(MAKE) GPU=0 ARCH=x86-64-v3 EXE=nexarch-cpu-avx2

gpu:
	$(MAKE) GPU=1 ARCH=x86-64-v3 EXE=nexarch-gpu

.PHONY: clean cpu cpu-avx2 gpu
