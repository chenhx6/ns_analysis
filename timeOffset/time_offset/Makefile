CXX = g++
CXXFLAGS = -O2 -Wall -Wextra -std=c++17
ROOTCFLAGS = $(shell root-config --cflags)
ROOTLIBS = $(shell root-config --libs)

all: time_offset

time_offset: time_offset.cc time_offset.hh
	$(CXX) $(CXXFLAGS) $(ROOTCFLAGS) time_offset.cc -o $@ $(ROOTLIBS)

check: time_offset
	./time_offset --self-check

clean:
	rm -f time_offset
.PHONY: all check clean
