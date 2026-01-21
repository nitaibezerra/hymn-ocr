#!/usr/bin/env python3
"""Validate OCR output against original YAML."""

import sys
from pathlib import Path
from difflib import SequenceMatcher

import yaml


def load_yaml(path: str) -> dict:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Remove extra whitespace, normalize newlines
    lines = [line.strip() for line in text.strip().split("\n")]
    return "\n".join(line for line in lines if line)


def text_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity ratio (0-1)."""
    t1 = normalize_text(text1)
    t2 = normalize_text(text2)
    return SequenceMatcher(None, t1, t2).ratio()


def validate_hymns(ocr_hymns: list, orig_hymns: list) -> dict:
    """Compare OCR hymns with original hymns."""
    results = {
        "total": len(orig_hymns),
        "title_match": 0,
        "text_match": 0,
        "text_similarity_avg": 0.0,
        "date_match": 0,
        "date_present": 0,
        "repetition_match": 0,
        "original_number_match": 0,
        "offered_to_match": 0,
        "style_match": 0,
        "issues": [],
    }

    text_similarities = []

    for i, (ocr, orig) in enumerate(zip(ocr_hymns, orig_hymns), 1):
        hymn_issues = []

        # Title comparison
        ocr_title = ocr.get("title", "").strip().lower()
        orig_title = orig.get("title", "").strip().lower()
        if ocr_title == orig_title:
            results["title_match"] += 1
        else:
            hymn_issues.append(f"title: '{ocr.get('title')}' vs '{orig.get('title')}'")

        # Text comparison
        ocr_text = normalize_text(ocr.get("text", ""))
        orig_text = normalize_text(orig.get("text", ""))
        similarity = text_similarity(ocr_text, orig_text)
        text_similarities.append(similarity)

        if similarity >= 0.95:
            results["text_match"] += 1
        elif similarity < 0.90:
            hymn_issues.append(f"text similarity: {similarity:.1%}")

        # Date comparison
        ocr_date = ocr.get("received_at")
        orig_date = orig.get("received_at")

        if ocr_date:
            results["date_present"] += 1
            # Normalize date format
            ocr_date_str = str(ocr_date).replace("'", "").replace('"', "")
            orig_date_str = str(orig_date) if orig_date else ""
            if ocr_date_str == orig_date_str:
                results["date_match"] += 1
            else:
                hymn_issues.append(f"date: '{ocr_date}' vs '{orig_date}'")
        elif orig_date:
            hymn_issues.append(f"date missing (expected: {orig_date})")

        # Repetition comparison
        ocr_rep = ocr.get("repetitions", "")
        orig_rep = orig.get("repetitions", "")
        if ocr_rep and orig_rep:
            # Normalize: remove spaces, sort
            ocr_rep_norm = ",".join(sorted(str(ocr_rep).replace(" ", "").split(",")))
            orig_rep_norm = ",".join(sorted(str(orig_rep).replace(" ", "").split(",")))
            if ocr_rep_norm == orig_rep_norm:
                results["repetition_match"] += 1
            else:
                hymn_issues.append(f"repetitions: '{ocr_rep}' vs '{orig_rep}'")
        elif orig_rep and not ocr_rep:
            hymn_issues.append(f"repetitions missing (expected: {orig_rep})")

        # Original number comparison
        ocr_orig_num = ocr.get("original_number")
        orig_num = orig.get("number")  # In original YAML, "number" is the original hymn number
        if ocr_orig_num and orig_num:
            if int(ocr_orig_num) == int(orig_num):
                results["original_number_match"] += 1
            else:
                hymn_issues.append(f"original_number: {ocr_orig_num} vs {orig_num}")

        # Offered_to comparison
        ocr_offered = (ocr.get("offered_to") or "").strip().lower()
        orig_offered = (orig.get("offered_to") or "").strip().lower()
        if ocr_offered == orig_offered:
            results["offered_to_match"] += 1
        elif ocr_offered or orig_offered:
            hymn_issues.append(f"offered_to: '{ocr.get('offered_to')}' vs '{orig.get('offered_to')}'")

        # Style comparison
        ocr_style = (ocr.get("style") or "").strip().lower()
        orig_style = (orig.get("style") or "").strip().lower()
        if ocr_style == orig_style:
            results["style_match"] += 1
        elif ocr_style or orig_style:
            hymn_issues.append(f"style: '{ocr.get('style')}' vs '{orig.get('style')}'")

        if hymn_issues:
            results["issues"].append({
                "hymn": i,
                "title": orig.get("title"),
                "problems": hymn_issues,
            })

    if text_similarities:
        results["text_similarity_avg"] = sum(text_similarities) / len(text_similarities)

    return results


def print_report(results: dict) -> None:
    """Print validation report."""
    total = results["total"]

    print("=" * 60)
    print("HYMN OCR VALIDATION REPORT")
    print("=" * 60)
    print()

    # Summary table
    print("FIELD MATCHING:")
    print("-" * 40)
    fields = [
        ("Title", results["title_match"], total),
        ("Text (95%+ similar)", results["text_match"], total),
        ("Date (present)", results["date_present"], total),
        ("Date (correct)", results["date_match"], total),
        ("Repetitions", results["repetition_match"], total),
        ("Original Number", results["original_number_match"], total),
        ("Offered To", results["offered_to_match"], total),
        ("Style", results["style_match"], total),
    ]

    for name, match, tot in fields:
        pct = (match / tot * 100) if tot > 0 else 0
        status = "✅" if pct >= 95 else "⚠️" if pct >= 80 else "❌"
        print(f"  {status} {name:.<25} {match:>3}/{tot} ({pct:>5.1f}%)")

    print()
    print(f"  Average text similarity: {results['text_similarity_avg']:.1%}")
    print()

    # Issues
    if results["issues"]:
        print("ISSUES BY HYMN:")
        print("-" * 40)
        for issue in results["issues"]:
            print(f"\n  Hymn #{issue['hymn']}: {issue['title']}")
            for problem in issue["problems"]:
                print(f"    - {problem}")

    print()
    print("=" * 60)

    # Overall score
    score = (
        results["title_match"]
        + results["text_match"]
        + results["date_match"]
        + results["repetition_match"]
        + results["original_number_match"]
    ) / (total * 5) * 100

    print(f"OVERALL SCORE: {score:.1f}%")
    print("=" * 60)


def main():
    if len(sys.argv) < 3:
        print("Usage: validate_ocr.py <ocr_output.yaml> <original.yaml>")
        sys.exit(1)

    ocr_path = sys.argv[1]
    orig_path = sys.argv[2]

    # Load files
    ocr_data = load_yaml(ocr_path)
    orig_data = load_yaml(orig_path)

    # Handle different structures
    ocr_hymns = ocr_data.get("hymns", [])
    orig_hymns = orig_data.get("hymn_book", {}).get("hymns", [])

    if not orig_hymns:
        orig_hymns = orig_data.get("hymns", [])

    print(f"OCR hymns: {len(ocr_hymns)}")
    print(f"Original hymns: {len(orig_hymns)}")
    print()

    # Validate
    results = validate_hymns(ocr_hymns, orig_hymns)

    # Print report
    print_report(results)


if __name__ == "__main__":
    main()
