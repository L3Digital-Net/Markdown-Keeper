---
title: Performance Benchmarking Methodology
tags: performance,benchmarking,testing
category: performance
concepts: benchmark,performance,latency,throughput,percentile
---

# Performance Benchmarking Methodology

Benchmarking without rigor produces numbers that are worse than useless: they create false confidence. This guide covers how to design benchmarks that yield actionable data, interpret results with appropriate skepticism, and communicate findings to stakeholders who may not share your statistical vocabulary.

## Benchmark Design and Statistical Significance

A benchmark measures a specific operation under controlled conditions. Define the operation precisely before writing any code. "Measure API performance" is not a benchmark; "measure p99 latency of the `/api/v1/query` endpoint under 200 concurrent connections with a 50/50 read-write mix" is.

Control for variability by fixing as many parameters as possible: hardware spec, OS tuning, background processes, dataset size, and warm-up duration. Run each benchmark a minimum of 30 iterations to establish a distribution. Report the median, p95, and p99, not the mean; means are distorted by outliers that percentiles handle gracefully. Include the standard deviation or interquartile range so readers can judge consistency.

Statistical significance matters when comparing two implementations. A 3% improvement that falls within the noise floor of your measurement is not an improvement; it is a coin flip. Use a paired t-test or Mann-Whitney U test to confirm that observed differences are real. If you cannot explain the statistics, at minimum run enough iterations that the confidence interval is narrower than the difference you are claiming.

Beware of microbenchmark traps. JIT compilers, CPU branch predictors, and OS page caches all optimize for repeated access patterns. A loop that calls the same function 10,000 times with identical input measures the best case, not the typical case. Randomize inputs, interleave operations, and include cold-start runs alongside warm-cache runs. Refer to [architecture decision records](./architecture-decision-records.md) for context on why specific benchmark parameters were chosen.

## Flame Graphs and Profiling

Before optimizing, profile. Flame graphs (popularized by Brendan Gregg) visualize where CPU time is spent across the entire call stack. Generate them using `perf` on Linux or `py-spy` for Python workloads. The x-axis represents the proportion of samples, not time; wider frames mean more samples, which correlates with more time spent.

Look for plateaus: wide frames that dominate the graph indicate hot paths worth optimizing. Narrow, deep stacks suggest recursive or deeply nested logic that may benefit from restructuring but rarely dominates total runtime.

Pair CPU flame graphs with off-CPU analysis to find time spent waiting on I/O, locks, or network calls. A service that spends 80% of wall-clock time waiting on database queries will not get faster from CPU optimization. The bottleneck is elsewhere, and the flame graph tells you exactly where.

## Load Testing and Reporting Results

For system-level benchmarks, use a load testing tool that supports controlled concurrency ramps: [k6](https://k6.io/), Locust, or wrk2. Start at a low request rate and increase linearly until throughput plateaus or error rates exceed your threshold (typically 0.1% for SLA-bound services). Record the saturation point; this is the system's practical capacity.

Present results as a summary table with columns for concurrency level, median latency, p99 latency, throughput (requests per second), and error rate. Include a latency-vs-throughput chart showing the inflection point where latency degrades. Raw data and the exact commands used to reproduce the benchmark should be committed to the repository alongside the report so that future runs can be compared apples-to-apples.

Always note the environment: hardware specs, OS version, runtime version, and dataset characteristics. A benchmark result without environment metadata is unreproducible, and an unreproducible benchmark is an anecdote. Store historical results in a `benchmarks/` directory so trends are visible over time, as described in the [project documentation guide](./project-documentation-guide.md).
