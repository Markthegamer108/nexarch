# Linux / Kaggle build:  make            -> ./nexarch tuned for this machine
#                        make ARCH=x86-64-v3   -> portable AVX2 build
EXE ?= nexarch
ARCH ?= native
CXXFLAGS ?= -O3 -std=c++20 -march=$(ARCH) -DNDEBUG -flto -pthread -Wall -Wextra
SOURCES := $(wildcard src/*.cpp)
HEADERS := $(wildcard src/*.h)

$(EXE): $(SOURCES) $(HEADERS)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $@ $(LDFLAGS)

clean:
	rm -f $(EXE)

.PHONY: clean
