CXX = g++
CXXFLAGS = -O2 -Wall -Wextra -pedantic $(shell root-config --cflags)
LDLIBS = $(shell root-config --libs)
SOURCE = ../../../time_offset/time_offset

all: build/verify

build/verify: verify.cc $(SOURCE)/time_offset.cc $(SOURCE)/time_offset.hh $(SOURCE)/UserDefine.hh
	mkdir -p build
	$(CXX) $(CXXFLAGS) verify.cc -o $@ $(LDLIBS)

check: build/verify
	./build/verify self

clean:
	rm -f build/verify
.PHONY: all check clean
