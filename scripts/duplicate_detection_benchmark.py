#!/usr/bin/env python3
"""Benchmark script for duplicate detection performance optimization."""

import random
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add .claude to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude"))

from tools.amplihack.reflection.duplicate_detection import (
    check_duplicate_issue,
    get_cache_manager,
    get_detection_engine,
    store_new_issue,
)


class DuplicateDetectionBenchmark:
    """Benchmark for duplicate detection performance."""

    def __init__(self):
        self.results = {}
        self.test_issues = []

    def generate_test_data(self, num_issues: int = 1000) -> List[Dict]:
        """Generate test issue data for benchmarking."""
        print(f"📝 Generating {num_issues} test issues...")

        test_data = []

        # Generate diverse content
        common_words = [
            "bug",
            "feature",
            "issue",
            "error",
            "problem",
            "request",
            "fix",
            "add",
            "update",
            "remove",
        ]
        technical_words = [
            "API",
            "database",
            "authentication",
            "performance",
            "security",
            "frontend",
            "backend",
        ]

        for i in range(num_issues):
            # Create varied issue content
            title_words = random.sample(common_words + technical_words, random.randint(2, 6))
            title = " ".join(title_words).title()

            # Create body with varying lengths
            body_length = random.choice([100, 500, 1000, 2000])  # Different content sizes
            body_sentences = []
            for _ in range(body_length // 50):
                sentence_words = random.sample(
                    common_words + technical_words, random.randint(5, 15)
                )
                body_sentences.append(" ".join(sentence_words))
            body = ". ".join(body_sentences)

            # Add some exact duplicates for testing (5%)
            if i > 0 and random.random() < 0.05:
                # Create exact duplicate of previous issue
                prev_issue = test_data[i - 1]
                title = prev_issue["title"]
                body = prev_issue["body"]

            # Add some similar issues for text similarity testing (10%)
            elif i > 0 and random.random() < 0.10:
                # Create similar issue with small variations
                prev_issue = test_data[random.randint(0, i - 1)]
                title = prev_issue["title"] + " (updated)"
                body = prev_issue["body"] + " Additional details."

            test_data.append(
                {
                    "issue_id": str(i + 1),
                    "title": title,
                    "body": body,
                    "pattern_type": random.choice(["bug", "feature", "enhancement", None]),
                }
            )

        return test_data

    def benchmark_hash_generation(self, test_data: List[Dict]) -> Dict:
        """Benchmark hash generation performance."""
        print("🔢 Benchmarking hash generation...")

        engine = get_detection_engine()
        hash_generator = engine.hash_generator

        times = []

        for issue in test_data[:100]:  # Test on subset for detailed timing
            start_time = time.perf_counter()
            hash_generator.generate_composite_hash(
                issue["title"], issue["body"], issue.get("pattern_type")
            )
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        return {
            "avg_hash_time_ms": (sum(times) / len(times)) * 1000,
            "total_hashes": len(times),
            "hash_rate_per_second": len(times) / sum(times) if sum(times) > 0 else 0,
        }

    def benchmark_cache_operations(self, test_data: List[Dict]) -> Dict:
        """Benchmark cache storage and retrieval performance."""
        print("💾 Benchmarking cache operations...")

        cache_manager = get_cache_manager()
        cache_manager.clear_cache()  # Start fresh

        # Storage performance
        storage_times = []
        for issue in test_data[:100]:  # Test storage on subset
            start_time = time.perf_counter()
            store_new_issue(
                issue["issue_id"], issue["title"], issue["body"], issue.get("pattern_type")
            )
            end_time = time.perf_counter()
            storage_times.append(end_time - start_time)

        # Retrieval performance (find similar)
        retrieval_times = []
        engine = get_detection_engine()
        test_hash = engine.hash_generator.generate_composite_hash("test", "test")

        for _ in range(50):  # Test retrieval
            start_time = time.perf_counter()
            cache_manager.find_similar_issues(test_hash)
            end_time = time.perf_counter()
            retrieval_times.append(end_time - start_time)

        return {
            "avg_storage_time_ms": (sum(storage_times) / len(storage_times)) * 1000,
            "avg_retrieval_time_ms": (sum(retrieval_times) / len(retrieval_times)) * 1000,
            "storage_rate_per_second": len(storage_times) / sum(storage_times)
            if sum(storage_times) > 0
            else 0,
            "cached_issues": len(cache_manager.get_all_issues()),
        }

    def benchmark_duplicate_detection(self, test_data: List[Dict]) -> Dict:
        """Benchmark full duplicate detection performance."""
        print("🔍 Benchmarking duplicate detection...")

        # Clear and populate cache with substantial data
        cache_manager = get_cache_manager()
        cache_manager.clear_cache()

        # Populate cache with first 80% of data
        cache_size = int(len(test_data) * 0.8)
        print(f"   Populating cache with {cache_size} issues...")

        for issue in test_data[:cache_size]:
            store_new_issue(
                issue["issue_id"], issue["title"], issue["body"], issue.get("pattern_type")
            )

        # Test duplicate detection on remaining 20%
        test_issues = test_data[cache_size:]
        detection_times = []
        duplicate_count = 0

        print(f"   Testing duplicate detection on {len(test_issues)} issues...")

        for issue in test_issues:
            start_time = time.perf_counter()
            result = check_duplicate_issue(issue["title"], issue["body"], issue.get("pattern_type"))
            end_time = time.perf_counter()

            detection_times.append(end_time - start_time)
            if result.is_duplicate:
                duplicate_count += 1

        avg_time = sum(detection_times) / len(detection_times) if detection_times else 0
        max_time = max(detection_times) if detection_times else 0

        return {
            "cache_size": cache_size,
            "test_issues": len(test_issues),
            "avg_detection_time_ms": avg_time * 1000,
            "max_detection_time_ms": max_time * 1000,
            "detection_rate_per_second": len(test_issues) / sum(detection_times)
            if sum(detection_times) > 0
            else 0,
            "duplicates_found": duplicate_count,
            "duplicate_rate": duplicate_count / len(test_issues) if test_issues else 0,
            "meets_5s_requirement": max_time < 5.0,
            "meets_2s_target": avg_time < 2.0,
        }

    def benchmark_text_similarity(self, test_data: List[Dict]) -> Dict:
        """Benchmark text similarity performance (the main bottleneck)."""
        print("📝 Benchmarking text similarity algorithm...")

        engine = get_detection_engine()
        hash_generator = engine.hash_generator

        # Test text similarity on various content sizes
        similarity_times = []
        content_sizes = []

        for i in range(0, min(100, len(test_data)), 2):
            issue1 = test_data[i]
            issue2 = test_data[i + 1] if i + 1 < len(test_data) else test_data[0]

            text1 = f"{issue1['title']} {issue1['body']}"
            text2 = f"{issue2['title']} {issue2['body']}"

            content_sizes.append(len(text1) + len(text2))

            start_time = time.perf_counter()
            hash_generator.calculate_text_similarity(text1, text2)
            end_time = time.perf_counter()

            similarity_times.append(end_time - start_time)

        return {
            "avg_similarity_time_ms": (sum(similarity_times) / len(similarity_times)) * 1000,
            "max_similarity_time_ms": max(similarity_times) * 1000,
            "avg_content_size": sum(content_sizes) / len(content_sizes),
            "similarity_rate_per_second": len(similarity_times) / sum(similarity_times)
            if sum(similarity_times) > 0
            else 0,
        }

    def run_comprehensive_benchmark(self, num_issues: int = 1000) -> Dict:
        """Run comprehensive performance benchmark."""
        print("🏁 Starting Duplicate Detection Performance Benchmark")
        print("=" * 60)

        # Generate test data
        test_data = self.generate_test_data(num_issues)

        # Run individual benchmarks
        results = {
            "test_configuration": {
                "num_issues": num_issues,
                "timestamp": time.time(),
            },
            "hash_generation": self.benchmark_hash_generation(test_data),
            "cache_operations": self.benchmark_cache_operations(test_data),
            "text_similarity": self.benchmark_text_similarity(test_data),
            "duplicate_detection": self.benchmark_duplicate_detection(test_data),
        }

        # Overall performance summary
        detection_result = results["duplicate_detection"]

        print("\n📊 Performance Summary:")
        print(f"   Average detection time: {detection_result['avg_detection_time_ms']:.2f}ms")
        print(f"   Maximum detection time: {detection_result['max_detection_time_ms']:.2f}ms")
        print(
            f"   Detection rate: {detection_result['detection_rate_per_second']:.1f} issues/second"
        )
        print(f"   Cache size tested: {detection_result['cache_size']} issues")
        print(
            f"   Meets 5s requirement: {'✅' if detection_result['meets_5s_requirement'] else '❌'}"
        )
        print(f"   Meets 2s target: {'✅' if detection_result['meets_2s_target'] else '❌'}")

        return results

    def analyze_bottlenecks(self, results: Dict) -> Dict:
        """Analyze results to identify performance bottlenecks."""
        print("\n🔬 Bottleneck Analysis:")

        bottlenecks = {}

        # Hash generation analysis
        hash_time = results["hash_generation"]["avg_hash_time_ms"]
        if hash_time > 10:  # 10ms threshold
            bottlenecks["hash_generation"] = f"Slow hash generation: {hash_time:.2f}ms avg"
            print(f"   ⚠️  Hash generation: {hash_time:.2f}ms (target: <10ms)")
        else:
            print(f"   ✅ Hash generation: {hash_time:.2f}ms")

        # Cache operations analysis
        storage_time = results["cache_operations"]["avg_storage_time_ms"]
        if storage_time > 50:  # 50ms threshold
            bottlenecks["cache_storage"] = f"Slow cache storage: {storage_time:.2f}ms avg"
            print(f"   ⚠️  Cache storage: {storage_time:.2f}ms (target: <50ms)")
        else:
            print(f"   ✅ Cache storage: {storage_time:.2f}ms")

        retrieval_time = results["cache_operations"]["avg_retrieval_time_ms"]
        if retrieval_time > 10:  # 10ms threshold
            bottlenecks["cache_retrieval"] = f"Slow cache retrieval: {retrieval_time:.2f}ms avg"
            print(f"   ⚠️  Cache retrieval: {retrieval_time:.2f}ms (target: <10ms)")
        else:
            print(f"   ✅ Cache retrieval: {retrieval_time:.2f}ms")

        # Text similarity analysis
        similarity_time = results["text_similarity"]["avg_similarity_time_ms"]
        if similarity_time > 20:  # 20ms threshold
            bottlenecks["text_similarity"] = f"Slow text similarity: {similarity_time:.2f}ms avg"
            print(f"   ⚠️  Text similarity: {similarity_time:.2f}ms (target: <20ms)")
        else:
            print(f"   ✅ Text similarity: {similarity_time:.2f}ms")

        # Overall detection time analysis
        max_detection_time = results["duplicate_detection"]["max_detection_time_ms"]
        if max_detection_time > 5000:  # 5s requirement
            bottlenecks["overall_performance"] = (
                f"Exceeds 5s requirement: {max_detection_time:.0f}ms max"
            )
            print(f"   ❌ Overall performance: {max_detection_time:.0f}ms (requirement: <5000ms)")
        else:
            print(f"   ✅ Overall performance: {max_detection_time:.0f}ms")

        return bottlenecks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark duplicate detection performance")
    parser.add_argument(
        "--issues", type=int, default=1000, help="Number of test issues to generate"
    )
    parser.add_argument("--output", type=str, help="Output file for results (optional)")

    args = parser.parse_args()

    benchmark = DuplicateDetectionBenchmark()
    results = benchmark.run_comprehensive_benchmark(args.issues)
    bottlenecks = benchmark.analyze_bottlenecks(results)

    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump({"results": results, "bottlenecks": bottlenecks}, f, indent=2)
        print(f"\n📁 Results saved to: {args.output}")
