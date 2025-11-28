#!/usr/bin/env python3
"""Realistic testing scenarios for slugify utility."""

import sys
from pathlib import Path

# Add src to path for import
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.utils.string_utils import slugify


def test_blog_post_titles():
    """Test slugify with realistic blog post titles."""
    print("\n=== Blog Post Titles ===")

    titles = [
        "10 Ways to Improve Your Python Code!",
        "What's New in Python 3.12?",
        "The Ultimate Guide to REST APIs (2024 Edition)",
        "Machine Learning: From Theory to Practice",
        "Why I Switched from VS Code to Vim... And Back Again",
    ]

    for title in titles:
        slug = slugify(title)
        print(f"'{title}' -> '{slug}'")


def test_product_names():
    """Test slugify with product names."""
    print("\n=== Product Names ===")

    products = [
        "iPhone 15 Pro Max (256GB)",
        "Dell XPS 13 - Intel® Core™ i7",
        "Sony WH-1000XM5 Wireless Noise-Canceling Headphones",
        'LG OLED65C3PUA 65" 4K Smart TV',
        'Microsoft Surface Pro 9 – 13" 2-in-1 Tablet',
    ]

    for product in products:
        slug = slugify(product, max_length=50)
        print(f"'{product}' -> '{slug}' (max 50 chars)")


def test_user_generated_content():
    """Test with messy user input."""
    print("\n=== User Generated Content ===")

    user_inputs = [
        "  Hello    World!!!   ",
        "café-René's amazing crêpes",
        "🔥 Hot Deal!!! 50% OFF 🎉",
        "Contact us @ info@example.com",
        "Price: $99.99 (was $149.99)",
    ]

    for input_text in user_inputs:
        slug = slugify(input_text)
        print(f"'{input_text}' -> '{slug}'")


def test_international_text():
    """Test with international characters."""
    print("\n=== International Text ===")

    international = [
        "Zürich hauptbahnhof",
        "São Paulo, Brazil",
        "Montréal, Québec",
        "Düsseldorf, Deutschland",
        "København (Copenhagen)",
    ]

    for text in international:
        slug = slugify(text)
        print(f"'{text}' -> '{slug}'")


def test_api_endpoints():
    """Test creating API endpoints from resource names."""
    print("\n=== API Endpoints ===")

    resources = [
        "User Profiles",
        "Shopping Cart Items",
        "Order History (Archived)",
        "Payment Methods",
        "Customer Reviews & Ratings",
    ]

    for resource in resources:
        endpoint = slugify(resource, separator="_")
        print(f"'{resource}' -> '/api/{endpoint}'")


def test_filename_generation():
    """Test generating safe filenames."""
    print("\n=== Safe Filenames ===")

    filenames = [
        "Report: Q4 2024 Financial Results.pdf",
        "John's Resume (Final Version).docx",
        "Meeting Notes - 12/25/2024 @ 3:00 PM",
        "Screenshot 2024-03-15 at 10.45.23 AM",
        "../../../etc/passwd",  # Path traversal attempt
    ]

    for filename in filenames:
        safe = slugify(filename, separator="_", max_length=100)
        print(f"'{filename}' -> '{safe}.pdf'")


def test_edge_cases():
    """Test edge cases and special scenarios."""
    print("\n=== Edge Cases ===")

    edge_cases = [
        "",  # Empty string
        "   ",  # Only whitespace
        "!!!",  # Only special chars
        "a",  # Single character
        "123456789",  # Only numbers
        "-_-_-",  # Only separators
        "It's a beautiful day, isn't it?",  # Contractions
        "C++ Programming & C# .NET Development",  # Programming languages
    ]

    for case in edge_cases:
        slug = slugify(case)
        print(f"'{case}' -> '{slug}'")


def test_idempotency():
    """Test that slugifying a slug returns the same slug."""
    print("\n=== Idempotency Test ===")

    original = "This is a Test String!!!"
    first_pass = slugify(original)
    second_pass = slugify(first_pass)
    third_pass = slugify(second_pass)

    print(f"Original: '{original}'")
    print(f"First pass: '{first_pass}'")
    print(f"Second pass: '{second_pass}'")
    print(f"Third pass: '{third_pass}'")
    print(f"Idempotent: {first_pass == second_pass == third_pass}")


def test_truncation_behavior():
    """Test max_length truncation behavior."""
    print("\n=== Truncation Behavior ===")

    long_text = "This is a very long title that needs to be truncated to fit within limits"

    for max_len in [10, 20, 30, 40]:
        slug = slugify(long_text, max_length=max_len)
        print(f"Max {max_len}: '{slug}' (actual: {len(slug)})")


def main():
    """Run all realistic tests."""
    print("=" * 60)
    print("REALISTIC SLUGIFY TESTING")
    print("=" * 60)

    test_blog_post_titles()
    test_product_names()
    test_user_generated_content()
    test_international_text()
    test_api_endpoints()
    test_filename_generation()
    test_edge_cases()
    test_idempotency()
    test_truncation_behavior()

    print("\n" + "=" * 60)
    print("ALL REALISTIC TESTS COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
