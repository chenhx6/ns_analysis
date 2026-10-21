CXX := g++
CXXFLAGS := -O2 -std=c++17 -Wall -Wextra $(shell root-config --cflags)
LIBS := $(shell root-config --libs) -lSpectrum

TARGET := autocal
SRCS := main.cc autocal.cc peakfinder.cc
OBJS := $(SRCS:.cc=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LIBS)

%.o: %.cc UserDefine.hh autocal.hh peakfinder.hh
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
