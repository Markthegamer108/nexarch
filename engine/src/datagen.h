// Self-play: generate training positions, and play matches between two versions of the engine.
#pragma once

#include <string>

// Arguments are key=value pairs, e.g. "threads=4 nodes=5000 seconds=3600 out=data.bin".
void run_datagen(const std::string& args);
void run_match(const std::string& args);
