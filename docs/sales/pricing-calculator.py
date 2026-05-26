"""
Recepta - ROI Calculator for Client Demos
Show potential clients exactly how much they're losing by NOT having an AI receptionist.
"""

import json
from datetime import datetime


def calculate_roi(
    business_name: str = "Your Business",
    daily_calls: int = 25,
    answer_rate: float = 0.55,
    avg_appointment_value: float = 250.0,
    avg_close_rate: float = 0.7,
    working_days_per_month: int = 22,
):
    """
    Calculate the ROI of implementing Recepta.

    Args:
        business_name: Name of the client's business
        daily_calls: Average calls per day
        answer_rate: Current percentage of calls answered (0.0 - 1.0)
        avg_appointment_value: Average revenue per booked appointment
        avg_close_rate: How many of the missed calls would have booked if answered
        working_days_per_month: Business days in a month
    """
    missed_per_day = daily_calls * (1 - answer_rate)
    missed_per_month = missed_per_day * working_days_per_month
    missed_per_year = missed_per_month * 12

    # Potential captured appointments
    potential_captured_per_month = missed_per_month * avg_close_rate

    # Revenue impact
    monthly_revenue_recovered = potential_captured_per_month * avg_appointment_value
    yearly_revenue_recovered = monthly_revenue_recovered * 12

    print(f"\n{'='*60}")
    print(f"  Recepta - ROI Analysis: {business_name}")
    print(f"  Date: {datetime.now().strftime('%B %d, %Y')}")
    print(f"{'='*60}\n")

    print("  CURRENT SITUATION:")
    print(f"  • Daily calls: {daily_calls}")
    print(f"  • Current answer rate: {answer_rate*100:.0f}%")
    print(f"  • Missed calls per day: {missed_per_day:.0f}")
    print(f"  • Missed calls per month: {missed_per_month:.0f}")
    print(f"  • Average appointment value: ${avg_appointment_value:,.2f}")
    print()

    print("  THE PROBLEM:")
    print(f"  • You're missing {missed_per_month:.0f} calls every month")
    print(f"  • At {avg_close_rate*100:.0f}% conversion, that's {potential_captured_per_month:.0f} lost appointments")
    print(f"  • Monthly lost revenue: ${missed_per_month * avg_appointment_value:,.2f}")
    print(f"  • Yearly lost revenue: ${missed_per_year * avg_appointment_value:,.2f}")
    print()

    print("  THE SOLUTION (Recepta):")
    print(f"  • 99%+ answer rate means capturing {missed_per_day:.0f} more calls/day")
    print(f"  • Potential monthly revenue recovered: ${monthly_revenue_recovered:,.2f}")
    print(f"  • Potential yearly revenue recovered: ${yearly_revenue_recovered:,.2f}")
    print()

    print("  YOUR INVESTMENT:")
    for tier_name, setup, monthly in [
        ("Starter", 1500, 300),
        ("Pro", 3000, 500),
        ("Enterprise", 5000, 800),
    ]:
        first_year_cost = setup + (monthly * 12)
        roi = ((yearly_revenue_recovered - first_year_cost) / first_year_cost) * 100
        print(f"  • {tier_name}: ${setup} setup + ${monthly}/mo")
        print(f"    Year 1 cost: ${first_year_cost:,}")
        print(f"    Year 1 return: ${yearly_revenue_recovered:,}")
        print(f"    ROI: {roi:.0f}%")
        print(f"    Breakeven: {setup / monthly_revenue_recovered:.1f} months")
        print()

    print("  BOTTOM LINE:")
    print(f"  For less than ${300} a month, you can recover")
    print(f"  over ${monthly_revenue_recovered:,.0f} in lost revenue every month.")
    print(f"  That's a {roi:.0f}% return on investment in year one.")
    print()

    return {
        "business": business_name,
        "daily_calls": daily_calls,
        "answer_rate": answer_rate,
        "missed_monthly": missed_per_month,
        "monthly_revenue_lost": missed_per_month * avg_appointment_value,
        "yearly_revenue_lost": missed_per_year * avg_appointment_value,
        "monthly_recovered": monthly_revenue_recovered,
        "yearly_recovered": yearly_revenue_recovered,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recepta ROI Calculator")
    parser.add_argument("--business", default="Your Business", help="Client business name")
    parser.add_argument("--calls", type=int, default=25, help="Daily call volume")
    parser.add_argument("--answer-rate", type=float, default=0.55, help="Current answer rate (0-1)")
    parser.add_argument("--avg-value", type=float, default=250, help="Average appointment value")

    args = parser.parse_args()

    calculate_roi(
        business_name=args.business,
        daily_calls=args.calls,
        answer_rate=args.answer_rate,
        avg_appointment_value=args.avg_value,
    )

    # Usage examples:
    # python docs/sales/pricing-calculator.py --business "SmileCare Dental" --calls 30 --answer-rate 0.6 --avg-value 300
    # python docs/sales/pricing-calculator.py --business "Smith Law Firm" --calls 15 --answer-rate 0.5 --avg-value 2000
    # python docs/sales/pricing-calculator.py --business "Quick Cool HVAC" --calls 20 --answer-rate 0.4 --avg-value 500
