/**
 * SYNTHETIC SAMPLE DATA. Newly authored for this prototype; not derived from any real person, account or dataset.
 *
 * How these were made: the request objects below were authored by hand (invented balances, dates and ids), then
 * passed once, at authoring time, through the repository's existing in-process API handlers to capture the exact
 * response envelope. (The uncertified sample was re-captured on 2026-10-25: the first request did not trigger the
 * engine's certification block, so it was not a real certified=false response; a scheduled foreign-currency debit with
 * no FX rate does.) This file is committed data: the client never recomputes, edits or derives any value in it.
 * Engine version of the captured responses: 1.0.0-pr1.1 (the approved baseline). Re-capture if the contract changes.
 */
import type { AnalysisRequestSample, AnalyzeResponse, ApiErrorResponse, ForecastResponse } from "../types/api.ts";

export const affordableNowRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 45
  },
  "events": [
    {
      "amount": "22000",
      "category": "rent",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-11-01",
      "event_id": "syn-rent",
      "status": "scheduled"
    },
    {
      "amount": "65000",
      "category": "salary",
      "currency": "INR",
      "direction": "credit",
      "event_date": "2026-11-05",
      "event_id": "syn-salary",
      "status": "scheduled"
    },
    {
      "amount": "3200.50",
      "category": "utilities",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-10-28",
      "event_id": "syn-utilities",
      "status": "scheduled"
    }
  ],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment",
      "installments",
      "partial",
      "wait",
      "full_payment_with_spending_changes"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "150000",
    "home_currency": "INR",
    "minimum_balance_to_keep": "30000"
  },
  "purchase": {
    "allows_partial_payment": true,
    "amount": "12000",
    "currency": "INR"
  }
};

export const affordableNowResponse: AnalyzeResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "de3e492ae19bc92d5a9cacace45b95ffaeb50f3f9d803cc9abb892a4dc6949dc",
  "outcome": {
    "certified": true,
    "status": "affordable_now"
  },
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      },
      {
        "code": "SCHEDULED_INCOME_COUNTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_summary": {
      "below_reserve": false,
      "days_below": 0,
      "first_breach_date": null,
      "last_breach_date": null,
      "lowest": {
        "balance": "124799.5",
        "day": "2026-11-01"
      },
      "max_shortfall": "0"
    },
    "candidates": [
      {
        "breach_days": [],
        "candidate_type": "full_payment",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PAY_NOW_SAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "12000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "12000"
      },
      {
        "breach_days": [],
        "candidate_type": "wait",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "FULL_PAYMENT_SAFE_FROM",
            "params": [
              [
                "date",
                "2026-10-24"
              ]
            ],
            "severity": "info"
          },
          {
            "code": "PAY_NOW_SAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "12000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "12000"
      },
      {
        "breach_days": [],
        "candidate_type": "full_payment",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PAY_NOW_SAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "12000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "12000"
      }
    ],
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2026-12-08",
      "horizon_end": "2026-12-08",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "certified": true,
    "chosen": {
      "breach_days": [],
      "candidate_type": "full_payment",
      "eligible": true,
      "final_payment_date": "2026-10-24",
      "first_payment_date": "2026-10-24",
      "option_id": null,
      "reasons": [
        {
          "code": "PAY_NOW_SAFE",
          "params": [],
          "severity": "info"
        }
      ],
      "rejection_code": null,
      "safe": true,
      "schedule": [
        {
          "amount": "12000",
          "currency": "INR",
          "due_date": "2026-10-24"
        }
      ],
      "spending_changes": [],
      "total_cost": "12000"
    },
    "considered_commitments": [],
    "data_quality": "high",
    "earliest_full_payment_date": "2026-10-24",
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 45,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "engine_version": "1.0.0-pr1.1",
    "fx_usage": [],
    "input_hash": "de3e492ae19bc92d5a9cacace45b95ffaeb50f3f9d803cc9abb892a4dc6949dc",
    "issues": [],
    "missing_information": [
      {
        "code": "DEADLINE_DEFAULTED",
        "field_name": "purchase.desired_completion_date",
        "impact": "informational",
        "subject_ids": []
      }
    ],
    "reasons": [
      {
        "code": "PAY_NOW_SAFE",
        "params": [],
        "severity": "info"
      },
      {
        "code": "LOWEST_POINT",
        "params": [
          [
            "balance",
            "124799.50"
          ],
          [
            "date",
            "2026-11-01"
          ]
        ],
        "severity": "info"
      }
    ],
    "status": "affordable_now",
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "a8da5f002f4efd6a822a1982534d0142c3911865f9ad3d37d0e3c67488d2cba4"
};

export const affordableWithPlanRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 75
  },
  "events": [
    {
      "amount": "65000",
      "category": "salary",
      "currency": "INR",
      "direction": "credit",
      "event_date": "2026-11-05",
      "event_id": "syn-salary-2",
      "status": "scheduled"
    }
  ],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment",
      "partial"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "75000",
    "home_currency": "INR",
    "minimum_balance_to_keep": "30000"
  },
  "purchase": {
    "allows_partial_payment": true,
    "amount": "60000",
    "currency": "INR"
  }
};

export const affordableWithPlanResponse: AnalyzeResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "a2a6ae256f1fe39a91f6a0677f951d3968b63f51ecb1a8d4ea8a0503e524c37f",
  "outcome": {
    "certified": true,
    "status": "affordable_with_plan"
  },
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      },
      {
        "code": "SCHEDULED_INCOME_COUNTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_summary": {
      "below_reserve": false,
      "days_below": 0,
      "first_breach_date": null,
      "last_breach_date": null,
      "lowest": {
        "balance": "75000",
        "day": "2026-10-24"
      },
      "max_shortfall": "0"
    },
    "candidates": [
      {
        "breach_days": [
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-24",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-25",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-26",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-27",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-28",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-29",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-30",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-10-31",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-11-01",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-11-02",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-11-03",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-11-04",
            "plan_low": "15000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "75000",
            "day": "2026-11-05",
            "plan_low": "15000",
            "reserve": "30000"
          }
        ],
        "candidate_type": "full_payment",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-24"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-25"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-26"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-27"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-28"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-29"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-30"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-31"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-01"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-02"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-03"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-04"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-05"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "REJECTED_UNSAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [
          {
            "amount": "60000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "60000"
      },
      {
        "breach_days": [],
        "candidate_type": "wait",
        "eligible": true,
        "final_payment_date": "2026-11-06",
        "first_payment_date": "2026-11-06",
        "option_id": null,
        "reasons": [
          {
            "code": "FULL_PAYMENT_SAFE_FROM",
            "params": [
              [
                "date",
                "2026-11-06"
              ]
            ],
            "severity": "info"
          },
          {
            "code": "PLAN_SAFE_WAIT",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "60000",
            "currency": "INR",
            "due_date": "2026-11-06"
          }
        ],
        "spending_changes": [],
        "total_cost": "60000"
      },
      {
        "breach_days": [],
        "candidate_type": "partial",
        "eligible": true,
        "final_payment_date": "2026-11-06",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PARTIAL_LIMITED_BY_SAFE_AMOUNT",
            "params": [],
            "severity": "info"
          },
          {
            "code": "PAY_NOW_SAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "45000",
            "currency": "INR",
            "due_date": "2026-10-24"
          },
          {
            "amount": "15000",
            "currency": "INR",
            "due_date": "2026-11-06"
          }
        ],
        "spending_changes": [],
        "total_cost": "60000"
      },
      {
        "breach_days": [],
        "candidate_type": "full_payment_with_spending_changes",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "NO_ELIGIBLE_FLEXIBLE_ITEMS",
            "params": [],
            "severity": "info"
          },
          {
            "code": "SPENDING_CHANGE_INSUFFICIENT",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "60000"
      }
    ],
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2027-01-07",
      "horizon_end": "2027-01-07",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "certified": true,
    "chosen": {
      "breach_days": [],
      "candidate_type": "partial",
      "eligible": true,
      "final_payment_date": "2026-11-06",
      "first_payment_date": "2026-10-24",
      "option_id": null,
      "reasons": [
        {
          "code": "PARTIAL_LIMITED_BY_SAFE_AMOUNT",
          "params": [],
          "severity": "info"
        },
        {
          "code": "PAY_NOW_SAFE",
          "params": [],
          "severity": "info"
        }
      ],
      "rejection_code": null,
      "safe": true,
      "schedule": [
        {
          "amount": "45000",
          "currency": "INR",
          "due_date": "2026-10-24"
        },
        {
          "amount": "15000",
          "currency": "INR",
          "due_date": "2026-11-06"
        }
      ],
      "spending_changes": [],
      "total_cost": "60000"
    },
    "considered_commitments": [],
    "data_quality": "high",
    "earliest_full_payment_date": "2026-11-06",
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 75,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "engine_version": "1.0.0-pr1.1",
    "fx_usage": [],
    "input_hash": "a2a6ae256f1fe39a91f6a0677f951d3968b63f51ecb1a8d4ea8a0503e524c37f",
    "issues": [],
    "missing_information": [
      {
        "code": "DEADLINE_DEFAULTED",
        "field_name": "purchase.desired_completion_date",
        "impact": "informational",
        "subject_ids": []
      }
    ],
    "reasons": [
      {
        "code": "PARTIAL_LIMITED_BY_SAFE_AMOUNT",
        "params": [],
        "severity": "info"
      },
      {
        "code": "PAY_NOW_SAFE",
        "params": [],
        "severity": "info"
      },
      {
        "code": "LOWEST_POINT",
        "params": [
          [
            "balance",
            "75000"
          ],
          [
            "date",
            "2026-10-24"
          ]
        ],
        "severity": "info"
      },
      {
        "code": "RESERVE_BREACH_IF_PAID_NOW",
        "params": [
          [
            "cause",
            "purchase_causes"
          ],
          [
            "date",
            "2026-10-24"
          ],
          [
            "shortfall",
            "15000.00"
          ]
        ],
        "severity": "warn"
      },
      {
        "code": "FULL_PAYMENT_SAFE_FROM",
        "params": [
          [
            "date",
            "2026-11-06"
          ]
        ],
        "severity": "info"
      }
    ],
    "status": "affordable_with_plan",
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "85563b7225d75319ce5718cb08ac6cfcb725548757cfaf9d5f12a2aec184f0ed"
};

export const affordableLaterRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 45
  },
  "events": [
    {
      "amount": "22000",
      "category": "rent",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-11-01",
      "event_id": "syn-rent",
      "status": "scheduled"
    },
    {
      "amount": "65000",
      "category": "salary",
      "currency": "INR",
      "direction": "credit",
      "event_date": "2026-11-05",
      "event_id": "syn-salary",
      "status": "scheduled"
    },
    {
      "amount": "3200.50",
      "category": "utilities",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-10-28",
      "event_id": "syn-utilities",
      "status": "scheduled"
    }
  ],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment",
      "wait"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "45000",
    "home_currency": "INR",
    "minimum_balance_to_keep": "30000"
  },
  "purchase": {
    "allows_partial_payment": false,
    "amount": "25000",
    "currency": "INR"
  }
};

export const affordableLaterResponse: AnalyzeResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "30ff101df89e88ea409029b7aab40b8d29d1e435181d42aab20591543436ac54",
  "outcome": {
    "certified": true,
    "status": "affordable_later"
  },
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      },
      {
        "code": "SCHEDULED_INCOME_COUNTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_summary": {
      "below_reserve": true,
      "days_below": 5,
      "first_breach_date": "2026-11-01",
      "last_breach_date": "2026-11-05",
      "lowest": {
        "balance": "19799.5",
        "day": "2026-11-01"
      },
      "max_shortfall": "10200.5"
    },
    "candidates": [
      {
        "breach_days": [
          {
            "attribution": "causes",
            "baseline_low": "45000",
            "day": "2026-10-24",
            "plan_low": "20000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "45000",
            "day": "2026-10-25",
            "plan_low": "20000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "45000",
            "day": "2026-10-26",
            "plan_low": "20000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "45000",
            "day": "2026-10-27",
            "plan_low": "20000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "41799.5",
            "day": "2026-10-28",
            "plan_low": "16799.5",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "41799.5",
            "day": "2026-10-29",
            "plan_low": "16799.5",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "41799.5",
            "day": "2026-10-30",
            "plan_low": "16799.5",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "41799.5",
            "day": "2026-10-31",
            "plan_low": "16799.5",
            "reserve": "30000"
          },
          {
            "attribution": "worsens",
            "baseline_low": "19799.5",
            "day": "2026-11-01",
            "plan_low": "-5200.5",
            "reserve": "30000"
          },
          {
            "attribution": "worsens",
            "baseline_low": "19799.5",
            "day": "2026-11-02",
            "plan_low": "-5200.5",
            "reserve": "30000"
          },
          {
            "attribution": "worsens",
            "baseline_low": "19799.5",
            "day": "2026-11-03",
            "plan_low": "-5200.5",
            "reserve": "30000"
          },
          {
            "attribution": "worsens",
            "baseline_low": "19799.5",
            "day": "2026-11-04",
            "plan_low": "-5200.5",
            "reserve": "30000"
          },
          {
            "attribution": "worsens",
            "baseline_low": "19799.5",
            "day": "2026-11-05",
            "plan_low": "-5200.5",
            "reserve": "30000"
          }
        ],
        "candidate_type": "full_payment",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-24"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-25"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-26"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-27"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-28"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-29"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-30"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-31"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_WORSENS_EXISTING_BREACH",
            "params": [
              [
                "date",
                "2026-11-01"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_WORSENS_EXISTING_BREACH",
            "params": [
              [
                "date",
                "2026-11-02"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_WORSENS_EXISTING_BREACH",
            "params": [
              [
                "date",
                "2026-11-03"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_WORSENS_EXISTING_BREACH",
            "params": [
              [
                "date",
                "2026-11-04"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_WORSENS_EXISTING_BREACH",
            "params": [
              [
                "date",
                "2026-11-05"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "REJECTED_UNSAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [
          {
            "amount": "25000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "25000"
      },
      {
        "breach_days": [],
        "candidate_type": "wait",
        "eligible": true,
        "final_payment_date": "2026-11-06",
        "first_payment_date": "2026-11-06",
        "option_id": null,
        "reasons": [
          {
            "code": "FULL_PAYMENT_SAFE_FROM",
            "params": [
              [
                "date",
                "2026-11-06"
              ]
            ],
            "severity": "info"
          },
          {
            "code": "PLAN_SAFE_WAIT",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": true,
        "schedule": [
          {
            "amount": "25000",
            "currency": "INR",
            "due_date": "2026-11-06"
          }
        ],
        "spending_changes": [],
        "total_cost": "25000"
      },
      {
        "breach_days": [],
        "candidate_type": "partial",
        "eligible": false,
        "final_payment_date": null,
        "first_payment_date": null,
        "option_id": null,
        "reasons": [
          {
            "code": "METHOD_NOT_ACCEPTED",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": "METHOD_NOT_ACCEPTED",
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "0"
      },
      {
        "breach_days": [],
        "candidate_type": "full_payment_with_spending_changes",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "NO_ELIGIBLE_FLEXIBLE_ITEMS",
            "params": [],
            "severity": "info"
          },
          {
            "code": "SPENDING_CHANGE_INSUFFICIENT",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "25000"
      }
    ],
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2026-12-08",
      "horizon_end": "2026-12-08",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "certified": true,
    "chosen": {
      "breach_days": [],
      "candidate_type": "wait",
      "eligible": true,
      "final_payment_date": "2026-11-06",
      "first_payment_date": "2026-11-06",
      "option_id": null,
      "reasons": [
        {
          "code": "FULL_PAYMENT_SAFE_FROM",
          "params": [
            [
              "date",
              "2026-11-06"
            ]
          ],
          "severity": "info"
        },
        {
          "code": "PLAN_SAFE_WAIT",
          "params": [],
          "severity": "info"
        }
      ],
      "rejection_code": null,
      "safe": true,
      "schedule": [
        {
          "amount": "25000",
          "currency": "INR",
          "due_date": "2026-11-06"
        }
      ],
      "spending_changes": [],
      "total_cost": "25000"
    },
    "considered_commitments": [],
    "data_quality": "high",
    "earliest_full_payment_date": "2026-11-06",
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 45,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "engine_version": "1.0.0-pr1.1",
    "fx_usage": [],
    "input_hash": "30ff101df89e88ea409029b7aab40b8d29d1e435181d42aab20591543436ac54",
    "issues": [],
    "missing_information": [
      {
        "code": "DEADLINE_DEFAULTED",
        "field_name": "purchase.desired_completion_date",
        "impact": "informational",
        "subject_ids": []
      }
    ],
    "reasons": [
      {
        "code": "FULL_PAYMENT_SAFE_FROM",
        "params": [
          [
            "date",
            "2026-11-06"
          ]
        ],
        "severity": "info"
      },
      {
        "code": "PLAN_SAFE_WAIT",
        "params": [],
        "severity": "info"
      },
      {
        "code": "LOWEST_POINT",
        "params": [
          [
            "balance",
            "19799.50"
          ],
          [
            "date",
            "2026-11-01"
          ]
        ],
        "severity": "info"
      },
      {
        "code": "BASELINE_BELOW_RESERVE",
        "params": [
          [
            "days",
            "5"
          ],
          [
            "first",
            "2026-11-01"
          ],
          [
            "last",
            "2026-11-05"
          ],
          [
            "max_shortfall",
            "10200.50"
          ]
        ],
        "severity": "warn"
      },
      {
        "code": "RESERVE_BREACH_IF_PAID_NOW",
        "params": [
          [
            "cause",
            "purchase_causes"
          ],
          [
            "date",
            "2026-10-24"
          ],
          [
            "shortfall",
            "10000.00"
          ]
        ],
        "severity": "warn"
      },
      {
        "code": "FULL_PAYMENT_SAFE_FROM",
        "params": [
          [
            "date",
            "2026-11-06"
          ]
        ],
        "severity": "info"
      }
    ],
    "status": "affordable_later",
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "9e37e2b9ad0cb7ffd5c8aeffe0698661c5b23465ba8303a3a2e031bd3b4f0f6c"
};

export const notAffordableRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 45
  },
  "events": [],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "40000",
    "home_currency": "INR",
    "minimum_balance_to_keep": "30000"
  },
  "purchase": {
    "allows_partial_payment": false,
    "amount": "90000",
    "currency": "INR"
  }
};

export const notAffordableResponse: AnalyzeResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "0b2e6610908dc71002a65d43b11426e0f11bb476e0ee02f165eeddc4b7b15396",
  "outcome": {
    "certified": true,
    "status": "not_affordable"
  },
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_summary": {
      "below_reserve": false,
      "days_below": 0,
      "first_breach_date": null,
      "last_breach_date": null,
      "lowest": {
        "balance": "40000",
        "day": "2026-10-24"
      },
      "max_shortfall": "0"
    },
    "candidates": [
      {
        "breach_days": [
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-24",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-25",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-26",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-27",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-28",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-29",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-30",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-10-31",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-01",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-02",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-03",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-04",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-05",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-06",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-07",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-08",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-09",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-10",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-11",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-12",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-13",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-14",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-15",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-16",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-17",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-18",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-19",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-20",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-21",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-22",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-23",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-24",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-25",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-26",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-27",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-28",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-29",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-11-30",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-01",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-02",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-03",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-04",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-05",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-06",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-07",
            "plan_low": "-50000",
            "reserve": "30000"
          },
          {
            "attribution": "causes",
            "baseline_low": "40000",
            "day": "2026-12-08",
            "plan_low": "-50000",
            "reserve": "30000"
          }
        ],
        "candidate_type": "full_payment",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-24"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-25"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-26"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-27"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-28"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-29"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-30"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-10-31"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-01"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-02"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-03"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-04"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-05"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-06"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-07"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-08"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-09"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-10"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-11"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-12"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-13"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-14"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-15"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-16"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-17"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-18"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-19"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-20"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-21"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-22"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-23"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-24"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-25"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-26"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-27"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-28"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-29"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-11-30"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-01"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-02"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-03"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-04"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-05"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-06"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-07"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "PURCHASE_CAUSES_BREACH",
            "params": [
              [
                "date",
                "2026-12-08"
              ]
            ],
            "severity": "warn"
          },
          {
            "code": "REJECTED_UNSAFE",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [
          {
            "amount": "90000",
            "currency": "INR",
            "due_date": "2026-10-24"
          }
        ],
        "spending_changes": [],
        "total_cost": "90000"
      },
      {
        "breach_days": [],
        "candidate_type": "wait",
        "eligible": false,
        "final_payment_date": null,
        "first_payment_date": null,
        "option_id": null,
        "reasons": [
          {
            "code": "NO_SAFE_OPTION",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": "NO_SAFE_OPTION",
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "0"
      },
      {
        "breach_days": [],
        "candidate_type": "partial",
        "eligible": false,
        "final_payment_date": null,
        "first_payment_date": null,
        "option_id": null,
        "reasons": [
          {
            "code": "METHOD_NOT_ACCEPTED",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": "METHOD_NOT_ACCEPTED",
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "0"
      },
      {
        "breach_days": [],
        "candidate_type": "full_payment_with_spending_changes",
        "eligible": true,
        "final_payment_date": "2026-10-24",
        "first_payment_date": "2026-10-24",
        "option_id": null,
        "reasons": [
          {
            "code": "NO_ELIGIBLE_FLEXIBLE_ITEMS",
            "params": [],
            "severity": "info"
          },
          {
            "code": "SPENDING_CHANGE_INSUFFICIENT",
            "params": [],
            "severity": "info"
          }
        ],
        "rejection_code": null,
        "safe": false,
        "schedule": [],
        "spending_changes": [],
        "total_cost": "90000"
      }
    ],
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2026-12-08",
      "horizon_end": "2026-12-08",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "certified": true,
    "chosen": null,
    "considered_commitments": [],
    "data_quality": "high",
    "earliest_full_payment_date": null,
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 45,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "engine_version": "1.0.0-pr1.1",
    "fx_usage": [],
    "input_hash": "0b2e6610908dc71002a65d43b11426e0f11bb476e0ee02f165eeddc4b7b15396",
    "issues": [],
    "missing_information": [
      {
        "code": "DEADLINE_DEFAULTED",
        "field_name": "purchase.desired_completion_date",
        "impact": "informational",
        "subject_ids": []
      }
    ],
    "reasons": [
      {
        "code": "NO_SAFE_OPTION",
        "params": [],
        "severity": "info"
      },
      {
        "code": "LOWEST_POINT",
        "params": [
          [
            "balance",
            "40000"
          ],
          [
            "date",
            "2026-10-24"
          ]
        ],
        "severity": "info"
      },
      {
        "code": "RESERVE_BREACH_IF_PAID_NOW",
        "params": [
          [
            "cause",
            "purchase_causes"
          ],
          [
            "date",
            "2026-10-24"
          ],
          [
            "shortfall",
            "80000.00"
          ]
        ],
        "severity": "warn"
      }
    ],
    "status": "not_affordable",
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "604d5f013bab1bc5506f847601d818ae30f03b34602637d399e9ed21140ac278"
};

export const uncertifiedRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 30
  },
  "events": [
    {
      "amount": "500",
      "category": "other",
      "currency": "ZAR",
      "direction": "debit",
      "event_date": "2026-10-28",
      "event_id": "syn-overseas-fee",
      "status": "scheduled"
    }
  ],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment",
      "installments",
      "partial",
      "wait",
      "full_payment_with_spending_changes"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "90000",
    "home_currency": "INR",
    "minimum_balance_to_keep": "20000"
  },
  "purchase": {
    "allows_partial_payment": true,
    "amount": "5000",
    "currency": "INR"
  }
};

export const uncertifiedResponse: AnalyzeResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "c747df03b6eab2086ce67494ed25a72296d5eebcf2223c54a44b9770c55b47f9",
  "outcome": {
    "certified": false,
    "status": null
  },
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_summary": {
      "below_reserve": false,
      "days_below": 0,
      "first_breach_date": null,
      "last_breach_date": null,
      "lowest": null,
      "max_shortfall": "0"
    },
    "candidates": [],
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2026-11-23",
      "horizon_end": "2026-11-23",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "certified": false,
    "chosen": null,
    "considered_commitments": [],
    "data_quality": "insufficient",
    "earliest_full_payment_date": null,
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 30,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "engine_version": "1.0.0-pr1.1",
    "fx_usage": [
      {
        "base_currency": "ZAR",
        "candidates_considered": null,
        "count": 1,
        "direction": "debit",
        "inverse_used_count": 0,
        "quote_currency": "INR",
        "stage": "unresolved",
        "window_days": null,
        "worst_age_days": null,
        "worst_rate": null
      }
    ],
    "input_hash": "c747df03b6eab2086ce67494ed25a72296d5eebcf2223c54a44b9770c55b47f9",
    "issues": [
      {
        "code": "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION",
        "params": [],
        "severity": "blocking"
      }
    ],
    "missing_information": [
      {
        "code": "DEADLINE_DEFAULTED",
        "field_name": "purchase.desired_completion_date",
        "impact": "informational",
        "subject_ids": []
      }
    ],
    "reasons": [
      {
        "code": "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION",
        "params": [],
        "severity": "blocking"
      }
    ],
    "status": null,
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "9fdb653e7b2f919c9eccd6ccc4c569b8f18b7828ed7805a451f288426df77071"
};

export const dashboardRequest: AnalysisRequestSample = {
  "as_of": "2026-10-24",
  "config": {
    "horizon_days": 30
  },
  "events": [
    {
      "amount": "22000",
      "category": "rent",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-11-01",
      "event_id": "syn-rent",
      "status": "scheduled"
    },
    {
      "amount": "65000",
      "category": "salary",
      "currency": "INR",
      "direction": "credit",
      "event_date": "2026-11-05",
      "event_id": "syn-salary",
      "status": "scheduled"
    },
    {
      "amount": "3200.50",
      "category": "utilities",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-10-28",
      "event_id": "syn-utilities",
      "status": "scheduled"
    },
    {
      "amount": "5400.25",
      "category": "groceries",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-11-10",
      "event_id": "syn-groceries",
      "status": "scheduled"
    },
    {
      "amount": "1180",
      "category": "utilities",
      "currency": "INR",
      "direction": "debit",
      "event_date": "2026-11-12",
      "event_id": "syn-internet",
      "status": "scheduled"
    }
  ],
  "payment_options": [],
  "preferences": {
    "accepted_methods": [
      "full_payment",
      "installments",
      "partial",
      "wait",
      "full_payment_with_spending_changes"
    ],
    "max_installment_term_days": 90
  },
  "profile": {
    "balance_as_of": "2026-10-24",
    "current_available_balance": "84250.75",
    "home_currency": "INR",
    "minimum_balance_to_keep": "30000"
  },
  "purchase": {
    "allows_partial_payment": true,
    "amount": "1000",
    "currency": "INR"
  }
};

export const dashboardForecast: ForecastResponse = {
  "api_version": "v1",
  "engine_version": "1.0.0-pr1.1",
  "input_hash": "48e7e54029e964921db49a858a7d731263a91ee034cb50df83cef01639ea30cf",
  "result": {
    "assumptions": [
      {
        "code": "DEADLINE_DEFAULTED",
        "params": [],
        "severity": "info"
      },
      {
        "code": "SCHEDULED_INCOME_COUNTED",
        "params": [],
        "severity": "info"
      }
    ],
    "baseline_series": [
      {
        "close": "84250.75",
        "day": "2026-10-24",
        "low": "84250.75"
      },
      {
        "close": "84250.75",
        "day": "2026-10-25",
        "low": "84250.75"
      },
      {
        "close": "84250.75",
        "day": "2026-10-26",
        "low": "84250.75"
      },
      {
        "close": "84250.75",
        "day": "2026-10-27",
        "low": "84250.75"
      },
      {
        "close": "81050.25",
        "day": "2026-10-28",
        "low": "81050.25"
      },
      {
        "close": "81050.25",
        "day": "2026-10-29",
        "low": "81050.25"
      },
      {
        "close": "81050.25",
        "day": "2026-10-30",
        "low": "81050.25"
      },
      {
        "close": "81050.25",
        "day": "2026-10-31",
        "low": "81050.25"
      },
      {
        "close": "59050.25",
        "day": "2026-11-01",
        "low": "59050.25"
      },
      {
        "close": "59050.25",
        "day": "2026-11-02",
        "low": "59050.25"
      },
      {
        "close": "59050.25",
        "day": "2026-11-03",
        "low": "59050.25"
      },
      {
        "close": "59050.25",
        "day": "2026-11-04",
        "low": "59050.25"
      },
      {
        "close": "124050.25",
        "day": "2026-11-05",
        "low": "59050.25"
      },
      {
        "close": "124050.25",
        "day": "2026-11-06",
        "low": "124050.25"
      },
      {
        "close": "124050.25",
        "day": "2026-11-07",
        "low": "124050.25"
      },
      {
        "close": "124050.25",
        "day": "2026-11-08",
        "low": "124050.25"
      },
      {
        "close": "124050.25",
        "day": "2026-11-09",
        "low": "124050.25"
      },
      {
        "close": "118650",
        "day": "2026-11-10",
        "low": "118650"
      },
      {
        "close": "118650",
        "day": "2026-11-11",
        "low": "118650"
      },
      {
        "close": "117470",
        "day": "2026-11-12",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-13",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-14",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-15",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-16",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-17",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-18",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-19",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-20",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-21",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-22",
        "low": "117470"
      },
      {
        "close": "117470",
        "day": "2026-11-23",
        "low": "117470"
      }
    ],
    "baseline_summary": {
      "below_reserve": false,
      "days_below": 0,
      "first_breach_date": null,
      "last_breach_date": null,
      "lowest": {
        "balance": "59050.25",
        "day": "2026-11-01"
      },
      "max_shortfall": "0"
    },
    "certifiable_window": {
      "deadline": null,
      "effective_end": "2026-11-23",
      "horizon_end": "2026-11-23",
      "max_window_days": 180,
      "start": "2026-10-24",
      "truncated": false
    },
    "considered_commitments": [],
    "engine_config_echo": {
      "balance_stale_after_days": 7,
      "commitment_overlap_amount_tolerance": "0.1",
      "commitment_overlap_day_tolerance": 3,
      "fx_pessimistic_window_days": 180,
      "fx_pivot_currencies": [
        "USD",
        "EUR"
      ],
      "fx_prior_window_days": 45,
      "horizon_days": 30,
      "max_spending_change_actions": 3,
      "max_window_days": 180,
      "variable_spend_lookback_days": 56,
      "variable_spend_min_history_days": 14,
      "variable_spend_min_weeks_for_percentile": 4
    },
    "fx_usage": [],
    "input_hash": "48e7e54029e964921db49a858a7d731263a91ee034cb50df83cef01639ea30cf",
    "issues": [],
    "variable_spend": {
      "categories": [],
      "complete_weeks_used": 0,
      "currency": null,
      "daily_amount": null,
      "estimated": false,
      "history_days": 0,
      "lookback_days": 56,
      "method": "weekly_p75_nearest_rank_v1",
      "statistic": "none",
      "weekly_totals": [],
      "weekly_value": null,
      "zero_weeks": 0
    }
  },
  "result_hash": "d8c16d52eb9e9201b248959d9a178f783fd8c278603b1c9fe8a61ce39fe13916"
};

export const validationErrorResponse: ApiErrorResponse = {
  "status": 422,
  "body": {
    "error": {
      "code": "invalid_request",
      "violations": [
        "purchase.amount:value_error",
        "unknown_field:extra_forbidden"
      ]
    }
  }
};

export const generalErrorResponse: ApiErrorResponse = {
  "status": 500,
  "body": {
    "error": {
      "code": "internal_error"
    }
  }
};
