#include "time_offset.hh"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

// run必填，拒绝尾随字符、符号和超范围编号。
int main(int argc, char **argv) {
    try {
        if(argc!=2) throw std::runtime_error("Usage: ./time_offset <run>");
        std::string arg=argv[1];
        if(arg.empty() || arg.find_first_not_of("0123456789")!=std::string::npos)
            throw std::runtime_error("Usage: ./time_offset <run>; run must be a positive integer");
        auto run=std::stoll(arg);
        if(run<=0 || run>std::numeric_limits<int>::max()) throw std::runtime_error("Invalid run");
        TimeOffset().Process(static_cast<int>(run));
        return 0;
    } catch(const std::exception &e) { std::cerr<<"Error: "<<e.what()<<'\n'; return 1; }
}
