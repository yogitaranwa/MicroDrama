RATES_PER_S = {
    "ltx-2.5@480p": 24,
    "ltx-2.5@720p": 48,
    "kling-3.0@720p": 72,
}

class BudgetExceeded(Exception):
    pass

class CostGovernor:
    def __init__(self, ceiling, reserve=0):
        self.ceiling = ceiling
        self.reserve = reserve
        self.planned = 0
        self.spent = 0

    def estimate(self, model_key, dur_s):
        if model_key not in RATES_PER_S:
            raise KeyError("unknown model key " + model_key)
        return int(RATES_PER_S[model_key] * dur_s)

    def approve(self, credits):
        if self.spent + self.planned + credits > self.ceiling - self.reserve:
            raise BudgetExceeded(f"{credits} credits would pass the ceiling {self.ceiling} with reserve {self.reserve}")
        self.planned += credits

    def record_spend(self, credits):
        self.spent += credits
        self.planned = max(0, self.planned - credits)

def plan_episode(script, model_key="kling-3.0@720p"):
    shots = script.shots
    hero = set()
    hero.add(shots[0].idx)
    for s in shots:
        if s.beat == "twist":
            hero.add(s.idx)
            break
    hero.add(shots[-1].idx)
    gov = CostGovernor(10**9)
    plan = []
    for s in shots:
        is_hero = s.idx in hero
        credits = gov.estimate(model_key, s.dur_s) if is_hero else 0
        plan.append({"shot": s.idx, "dur_s": s.dur_s, "mode": "video_hero" if is_hero else "still_with_motion", "est_credits": credits})
    return plan, sum(p["est_credits"] for p in plan)
