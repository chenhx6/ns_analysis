#include "autocal.hh"
#include <iostream>
#include <sstream>
#include <filesystem>
#include "TROOT.h"
#include "TError.h"

namespace fs = std::filesystem;

// DecodeAndSortAll direct style: no artificial root guessing, natural exe-local fallback
int main(int argc, char** argv) {
    try {
        gROOT->SetBatch(true);
        gErrorIgnoreLevel = kWarning;
        Settings s;

        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--help") {
                std::cout << "Usage: ./autocal [--input FILE] [--output DIR] [--source-library CSV] [--sources NAME,NAME] [--exclude cid:sid:ch] [--max-entries N] [--export-only]\n";
                return 0;
            }
            if (arg == "--export-only") { s.export_only = true; continue; }
            if (++i >= argc) throw std::runtime_error("missing value for " + arg);
            std::string value = argv[i];
            if (arg == "--input") s.input = value;
            else if (arg == "--output") s.output = value;
            else if (arg == "--source-library") s.library = value;
            else if (arg == "--max-entries") s.max_entries = std::stoll(value);
            else if (arg == "--sources") {
                s.sources.clear(); std::istringstream in(value); std::string name;
                while (std::getline(in, name, ',')) s.sources.push_back(name);
            } else if (arg == "--exclude") {
                int c = -1, d = -1, e = -1; char tail = 0;
                if (std::sscanf(value.c_str(), "%d:%d:%d%c", &c, &d, &e, &tail) != 3)
                    throw std::runtime_error("invalid exclusion triple");
                s.excluded.push_back({short(c), short(d), short(e)});
            } else throw std::runtime_error("unknown option " + arg);
        }

        if (s.input.empty()) s.input = User::InputFile;
        if (s.library.empty()) s.library = User::SourceLibrary;
        if (s.output.empty()) {
            s.output = fs::path(User::OutputDir) / fs::path(s.input).stem();
        }

        // Direct fallback: if library not found in cwd, check directly beside the executable
        if (!fs::exists(s.library)) {
            auto exe_dir = fs::canonical("/proc/self/exe").parent_path();
            if (fs::exists(exe_dir / s.library)) s.library = exe_dir / s.library;
            else if (fs::exists(exe_dir / s.library.filename())) s.library = exe_dir / s.library.filename();
        }

        return Run(s);
    } catch (const std::exception& e) {
        std::cerr << "autocal: " << e.what() << '\n';
        return 1;
    }
}
