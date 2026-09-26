#!/usr/bin/env python3
"""Read-only Google Ads account audit: performance, impression share, quality
scores, ads, assets, settings and Keyword Planner metrics for every enabled
campaign. Prints a compact report; changes nothing.

    source .venv/bin/activate
    python scripts/reports/account_audit.py [--days 90]
"""

import argparse
import datetime
from collections import defaultdict

from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "8733881378"
GREATER_LONDON = "geoTargetConstants/9041106"
ENGLISH = "languageConstants/1000"


def gbp(micros):
    return f"£{micros / 1e6:,.2f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=90)
    args = p.parse_args()
    c = GoogleAdsClient.load_from_storage()
    ga = c.get_service("GoogleAdsService")
    end = datetime.date.today()
    start = end - datetime.timedelta(days=args.days)
    span = f"segments.date BETWEEN '{start}' AND '{end}'"

    def q(query):
        return list(ga.search(customer_id=CUSTOMER_ID, query=query))

    print(f"== Campaigns, last {args.days} days ({start} to {end})")
    for r in q(f"""SELECT campaign.id, campaign.name, campaign.status, campaign.bidding_strategy_type,
            campaign.target_spend.cpc_bid_ceiling_micros, campaign_budget.amount_micros,
            campaign.geo_target_type_setting.positive_geo_target_type,
            metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc, metrics.cost_micros,
            metrics.search_impression_share, metrics.search_budget_lost_impression_share,
            metrics.search_rank_lost_impression_share, metrics.search_top_impression_share
            FROM campaign WHERE campaign.status = 'ENABLED' AND {span}"""):
        m, cp = r.metrics, r.campaign
        ceiling = cp.target_spend.cpc_bid_ceiling_micros
        print(f"{cp.name} [{cp.id}] {cp.bidding_strategy_type.name} ceiling={gbp(ceiling) if ceiling else 'none'} "
              f"budget={gbp(r.campaign_budget.amount_micros)}/day geo={cp.geo_target_type_setting.positive_geo_target_type.name}")
        print(f"   impr {m.impressions} · clicks {m.clicks} · CTR {m.ctr:.1%} · avg CPC {gbp(m.average_cpc)} · cost {gbp(m.cost_micros)}")
        print(f"   impression share {m.search_impression_share:.0%} · lost to budget {m.search_budget_lost_impression_share:.0%} "
              f"· lost to rank {m.search_rank_lost_impression_share:.0%} · top {m.search_top_impression_share:.0%}")

    print("\n== Keywords (quality score, performance)")
    kw_rows = q(f"""SELECT campaign.name, ad_group.name, ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type, ad_group_criterion.status,
            ad_group_criterion.quality_info.quality_score, ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.post_click_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.average_cpc
            FROM keyword_view WHERE campaign.status = 'ENABLED' AND {span}""")
    agg = {}
    for r in kw_rows:
        k = (r.campaign.name, r.ad_group_criterion.keyword.text.lower(), r.ad_group_criterion.keyword.match_type.name)
        a = agg.setdefault(k, {"imp": 0, "clk": 0, "cost": 0, "qs": None, "qi": r.ad_group_criterion.quality_info})
        a["imp"] += r.metrics.impressions; a["clk"] += r.metrics.clicks; a["cost"] += r.metrics.cost_micros
    for (camp, text, mt), a in sorted(agg.items(), key=lambda kv: -kv[1]["cost"]):
        qi = a["qi"]
        qs = qi.quality_score or "-"
        print(f"   {camp[:14]:<14} {mt[:6]:<6} {text[:38]:<38} QS {qs!s:<2} ad {qi.creative_quality_score.name[:5]:<5} "
              f"lp {qi.post_click_quality_score.name[:5]:<5} ctr {qi.search_predicted_ctr.name[:5]:<5} "
              f"| {a['imp']:>4} imp {a['clk']:>3} clk {gbp(a['cost']):>8}")

    all_kw = sorted({r.ad_group_criterion.keyword.text.lower() for r in q(
        "SELECT ad_group_criterion.keyword.text FROM ad_group_criterion WHERE ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND campaign.status = 'ENABLED' AND ad_group_criterion.status = 'ENABLED'")})

    print("\n== Ads")
    for r in q("""SELECT campaign.name, ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad_strength,
            ad_group_ad.policy_summary.approval_status, ad_group_ad.policy_summary.review_status,
            ad_group_ad.ad.final_urls, ad_group_ad.ad.type, ad_group_ad.status,
            ad_group_ad.ad.responsive_search_ad.headlines
            FROM ad_group_ad WHERE campaign.status = 'ENABLED' AND ad_group_ad.status != 'REMOVED'"""):
        a = r.ad_group_ad
        print(f"   {r.campaign.name[:14]:<14} {r.ad_group.name[:26]:<26} {a.ad.type_.name} strength={a.ad_strength.name} "
              f"policy={a.policy_summary.approval_status.name}/{a.policy_summary.review_status.name} "
              f"headlines={len(a.ad.responsive_search_ad.headlines)} → {', '.join(a.ad.final_urls)}")

    print("\n== Assets linked per campaign (type counts)")
    counts = defaultdict(lambda: defaultdict(int))
    for r in q("""SELECT campaign.name, campaign.status, campaign_asset.field_type, campaign_asset.status
            FROM campaign_asset WHERE campaign.status = 'ENABLED' AND campaign_asset.status = 'ENABLED'"""):
        counts[r.campaign.name][r.campaign_asset.field_type.name] += 1
    for r in q("SELECT customer_asset.field_type, customer_asset.status FROM customer_asset WHERE customer_asset.status = 'ENABLED'"):
        counts["(account-level)"][r.customer_asset.field_type.name] += 1
    for camp, d in counts.items():
        print(f"   {camp}: " + ", ".join(f"{k.lower()} {v}" for k, v in sorted(d.items())))

    print("\n== Targeting criteria per campaign")
    crit = defaultdict(list)
    for r in q("""SELECT campaign.name, campaign.status, campaign_criterion.type, campaign_criterion.location.geo_target_constant,
            campaign_criterion.ad_schedule.day_of_week, campaign_criterion.ad_schedule.start_hour,
            campaign_criterion.ad_schedule.end_hour, campaign_criterion.device.type,
            campaign_criterion.bid_modifier, campaign_criterion.user_interest.user_interest_category,
            campaign_criterion.negative
            FROM campaign_criterion WHERE campaign.status = 'ENABLED'"""):
        cc = r.campaign_criterion
        t = cc.type_.name
        if t == "KEYWORD":
            continue
        if t == "LOCATION":
            crit[r.campaign.name].append(f"location {cc.location.geo_target_constant.split('/')[-1]}")
        elif t == "AD_SCHEDULE":
            crit[r.campaign.name].append(f"{cc.ad_schedule.day_of_week.name[:3]} {cc.ad_schedule.start_hour}-{cc.ad_schedule.end_hour}")
        elif t == "DEVICE":
            crit[r.campaign.name].append(f"device {cc.device.type_.name} x{cc.bid_modifier or 1:.2f}")
        elif t == "USER_INTEREST":
            crit[r.campaign.name].append(f"audience {cc.user_interest.user_interest_category.split('/')[-1]} x{cc.bid_modifier or 1:.2f}")
        else:
            crit[r.campaign.name].append(t.lower())
    for camp, items in crit.items():
        print(f"   {camp}: " + "; ".join(items))

    print(f"\n== Keyword Planner: historical metrics for {len(all_kw)} live keywords (Greater London, English)")
    kp = c.get_service("KeywordPlanIdeaService")
    req = c.get_type("GenerateKeywordHistoricalMetricsRequest")
    req.customer_id = CUSTOMER_ID
    req.keywords.extend(all_kw)
    req.language = ENGLISH
    req.geo_target_constants.append(GREATER_LONDON)
    req.keyword_plan_network = c.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    for r in sorted(kp.generate_keyword_historical_metrics(request=req).results,
                    key=lambda r: -r.keyword_metrics.avg_monthly_searches):
        m = r.keyword_metrics
        print(f"   {r.text[:42]:<42} {m.avg_monthly_searches:>5}/mo {m.competition.name[:6]:<6} "
              f"top-of-page {gbp(m.low_top_of_page_bid_micros)}–{gbp(m.high_top_of_page_bid_micros)}")

    print("\n== Keyword Planner: ideas by theme (Greater London, ≥20 searches/mo)")
    seeds = {
        "funeral": ["funeral singers", "funeral choir", "singer for funeral", "funeral soloist"],
        "wedding": ["wedding choir", "wedding singers", "church wedding singer", "choir for wedding ceremony"],
        "christmas": ["carol singers", "christmas choir hire", "carol singers for hire", "christmas carol singers"],
    }
    live = set(all_kw)
    for theme, words in seeds.items():
        req = c.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = CUSTOMER_ID
        req.language = ENGLISH
        req.geo_target_constants.append(GREATER_LONDON)
        req.keyword_plan_network = c.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        req.keyword_seed.keywords.extend(words)
        ideas = [r for r in kp.generate_keyword_ideas(request=req) if r.keyword_idea_metrics.avg_monthly_searches >= 20]
        ideas.sort(key=lambda r: -r.keyword_idea_metrics.avg_monthly_searches)
        print(f"  [{theme}]")
        for r in ideas[:30]:
            m = r.keyword_idea_metrics
            vols = [v.monthly_searches for v in m.monthly_search_volumes]
            peak = max(vols) if vols else 0
            flag = "LIVE" if r.text.lower() in live else "    "
            print(f"   {flag} {r.text[:42]:<42} {m.avg_monthly_searches:>5}/mo (peak {peak}) {m.competition.name[:6]:<6} "
                  f"{gbp(m.low_top_of_page_bid_micros)}–{gbp(m.high_top_of_page_bid_micros)}")


if __name__ == "__main__":
    main()
