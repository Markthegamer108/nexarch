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
