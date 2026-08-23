"""The human-frozen S6 policy contract."""

SAME_DAY_DURATION_DAYS = 0
PRIMARY_METRIC = "30_DAY_CLOSURE_RATE"
SECONDARY_METRIC = "MEDIAN_CLOSURE_DURATION"
Q3_METRIC = "HIGH_PRIORITY_2024_VS_2025"
POLICY_IDS = {
    "same_day": "S6-POLICY-001",
    "primary_metric": "S6-POLICY-002",
    "secondary_metric": "S6-POLICY-003",
    "many_to_one": "S6-POLICY-004",
    "supplementary_only": "S6-POLICY-005",
    "invalid_comparison": "S6-POLICY-006",
    "category": "S6-POLICY-007",
    "q3": "S6-POLICY-008",
}
