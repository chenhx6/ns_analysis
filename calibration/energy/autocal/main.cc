#include "autocal.hh"
#include <iostream>
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
                std::cout << "Usage: ./autocal [--input FILE] [--output DIR] [--source-library CSV] [--exclude cid:sid:ch] [--max-entries N] [--export-only]\n"
                          << "Source selection is read only from UserDefine.hh::Sources.\n";
                return 0;
            }
            if (arg == "--export-only") { s.export_only = true; continue; }
            if (++i >= argc) throw std::runtime_error("missing value for " + arg);
            std::string value = argv[i];
            if (arg == "--input") s.input = value;
            else if (arg == "--output") s.output = value;
            else if (arg == "--source-library") s.library = value;
            else if (arg == "--max-entries") s.max_entries = std::stoll(value);
            else if (arg == "--exclude") {
                int c = -1, d = -1, e = -1; char tail = 0;
                if (std::sscanf(value.c_str(), "%d:%d:%d%c", &c, &d, &e, &tail) != 3)
                    throw std::runtime_error("invalid exclusion triple");
                s.excluded.push_back({short(c), short(d), short(e)});
            } else throw std::runtime_error("unknown option " + arg);
        }

        if (s.input.empty()) s.input = User::InputFile;
        if (s.library.empty()) s.library = User::SourceLibrary;

        // Resolve relative configuration paths from the project root, so the
        // same command works from the root or from calibration/energy/autocal.
        fs::path project_root = fs::current_path();
        fs::path exe_dir = fs::canonical("/proc/self/exe").parent_path();
        for (fs::path probe : {fs::current_path(), exe_dir, exe_dir.parent_path(),
                               exe_dir.parent_path().parent_path(),
                               exe_dir.parent_path().parent_path().parent_path()}) {
            if (fs::exists(probe / "calibration/energy/autocal")) {
                project_root = probe;
                break;
            }
        }
        auto resolve_input = [&](fs::path value) {
            if (value.is_absolute() || fs::exists(value)) return value;
            return project_root / value;
        };
        s.input = resolve_input(s.input);
        s.library = resolve_input(s.library);
        if (s.output.empty()) s.output = fs::path(User::OutputDir) / fs::path(s.input).stem();
        if (s.output.is_relative()) s.output = project_root / s.output;

        return Run(s);
    } catch (const std::exception& e) {
        std::cerr << "autocal: " << e.what() << '\n';
        return 1;
    }
}
