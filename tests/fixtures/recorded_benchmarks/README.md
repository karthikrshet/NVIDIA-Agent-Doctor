# Recorded Benchmark Evidence

This directory contains sanitized measurements captured from explicitly opted-in
benchmarks on authorized hardware. These values are workload-specific evidence,
not hardware specifications, performance claims, or regression thresholds.

Every fixture must state its exact command and limits, omit host-identifying
details and timestamps, and have a test that validates its schema and stated
non-topological claims. Do not place benchmark measurements in
`recorded_hardware/`, which is reserved for stable hardware facts.
