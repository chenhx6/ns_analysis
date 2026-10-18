CXX = g++
CXXFLAGS = -O2 -Wall -Wextra -pedantic $(shell root-config --cflags)
LDLIBS = $(shell root-config --libs)

all: time_offset

time_offset: main.cc time_offset.cc time_offset.hh UserDefine.hh
	$(CXX) $(CXXFLAGS) main.cc time_offset.cc -o $@ $(LDLIBS)

verify: verify.cc time_offset.cc time_offset.hh UserDefine.hh
	$(CXX) $(CXXFLAGS) verify.cc time_offset.cc -o $@ $(LDLIBS)

check: verify time_offset
	./verify self

clean:
	rm -f time_offset verify *.o
.PHONY: all check clean
