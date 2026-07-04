"""
Great Expectations Validation Suite

Validates data quality at each layer of the lakehouse:

Bronze checks:
  - Records exist (not empty)
  - Required fields present

Silver checks:
  - No duplicate IDs
  - Title is not null/empty
  - Status is from allowed values

Gold checks:
  - search_text field generated
  - enriched_at timestamp present
"""

import json
import os
from datetime import datetime
from backend.app.core.logger import logger


class DataValidator:
    """
    Custom validation suite implementing Great Expectations patterns.
    Each expectation returns pass/fail with details.
    """

    def __init__(self):
        self.results = []
        self.suite_name = ""

    def expect_table_row_count_to_be_greater_than(self, records: list, min_count: int):
        """Expect at least min_count records."""
        passed = len(records) > min_count
        self.results.append({
            "expectation": "expect_table_row_count_to_be_greater_than",
            "kwargs": {"min_count": min_count},
            "result": {"observed_value": len(records), "success": passed},
        })
        return passed

    def expect_column_values_to_not_be_null(self, records: list, column: str):
        """Expect no null values in a column."""
        nulls = sum(1 for r in records if not r.get(column))
        passed = nulls == 0
        self.results.append({
            "expectation": "expect_column_values_to_not_be_null",
            "kwargs": {"column": column},
            "result": {"null_count": nulls, "total": len(records), "success": passed},
        })
        return passed

    def expect_column_values_to_be_unique(self, records: list, column: str):
        """Expect unique values in a column."""
        values = [r.get(column) for r in records if r.get(column)]
        duplicates = len(values) - len(set(values))
        passed = duplicates == 0
        self.results.append({
            "expectation": "expect_column_values_to_be_unique",
            "kwargs": {"column": column},
            "result": {"duplicates": duplicates, "success": passed},
        })
        return passed

    def expect_column_values_to_be_in_set(self, records: list, column: str, value_set: list):
        """Expect column values to be from an allowed set."""
        invalid = [r.get(column) for r in records if r.get(column) not in value_set]
        passed = len(invalid) == 0
        self.results.append({
            "expectation": "expect_column_values_to_be_in_set",
            "kwargs": {"column": column, "value_set": value_set},
            "result": {"invalid_values": invalid[:5], "success": passed},
        })
        return passed

    def get_report(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["result"]["success"])
        return {
            "suite": self.suite_name,
            "timestamp": datetime.utcnow().isoformat(),
            "total_expectations": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            "results": self.results,
        }


def validate_bronze(records: list, entity_type: str) -> dict:
    """Validate bronze layer data."""
    v = DataValidator()
    v.suite_name = f"bronze_{entity_type}"
    v.expect_table_row_count_to_be_greater_than(records, 0)
    id_field = "nct_id" if entity_type == "clinical_trials" else "pmid"
    v.expect_column_values_to_not_be_null(records, id_field)
    v.expect_column_values_to_not_be_null(records, "title")
    return v.get_report()


def validate_silver(records: list, entity_type: str) -> dict:
    """Validate silver layer data."""
    v = DataValidator()
    v.suite_name = f"silver_{entity_type}"
    id_field = "nct_id" if entity_type == "clinical_trials" else "pmid"
    v.expect_column_values_to_be_unique(records, id_field)
    v.expect_column_values_to_not_be_null(records, "title")
    if entity_type == "clinical_trials":
        valid_statuses = [
            "Recruiting", "Completed", "Active, not recruiting",
            "Withdrawn", "Terminated", "Suspended", "Unknown",
            "Not yet recruiting", "Enrolling by invitation",
        ]
        v.expect_column_values_to_be_in_set(records, "status", valid_statuses)
    return v.get_report()


def validate_gold(records: list, entity_type: str) -> dict:
    """Validate gold layer data."""
    v = DataValidator()
    v.suite_name = f"gold_{entity_type}"
    v.expect_column_values_to_not_be_null(records, "search_text")
    v.expect_column_values_to_not_be_null(records, "enriched_at")
    v.expect_table_row_count_to_be_greater_than(records, 0)
    return v.get_report()
