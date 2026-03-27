#!/usr/bin/env python3
"""Build apps/api/config/daily_themes.json with 366 unique themes (one per calendar day, incl. leap years)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "api" / "config" / "daily_themes.json"

# Original editorial list (order preserved for first 30 days of the year in the old scheme;
# we now use day-of-year index into the full 366 list — Jan 1 = index 0, etc.)
ORIGINAL_30 = [
    "fear",
    "anxiety",
    "peace",
    "distraction",
    "prayer",
    "inner wholeness",
    "truth",
    "hypocrisy",
    "mercy",
    "forgiveness",
    "judgment",
    "enemy-love",
    "neighbor-love",
    "power",
    "humility",
    "suffering",
    "grief",
    "belonging",
    "loneliness",
    "trust",
    "wealth",
    "poverty",
    "justice",
    "discernment",
    "desire",
    "purity of heart",
    "hiddenness",
    "kingdom within",
    "watchfulness",
    "repentance",
]

# Additional single-phrase themes (contemplative / inner life). Must be unique (case-insensitive).
SUPPLEMENT = """
hope rest anger joy patience kindness doubt faith memory silence listening presence
awe beauty burden calling care change clarity comfort community compassion confession
confidence confusion contentment covenant creativity darkness dawn death devotion dignity
discipline distance dream duty ease emptiness endurance envy eternity expectation family
fasting fatigue fidelity finitude fire flow focus friendship fruitfulness gift glory grace
gratitude growth guilt habit healing heart heaven habit holiness honesty honor hunger
idolatry imagination impatience inclusion inheritance innocence integrity intention lament
law leadership learning letting go longing loss love loyalty lying margin marriage mind
mission money morning mystery naming nature neighbor night obedience offering openness pain
peacemaking persecution persistence place play pleasure praise prophecy protection purpose
question quiet rage readiness rebellion reconciliation redemption regret release remembrance
renewal resilience resistance restoration resurrection revelation reverence reward rhythm
righteousness ritual sacrifice sadness safety sanctification scarcity secrecy security
seeker self service shame simplicity sin sleep slowness sorrow soul speech spirit stability
stewardship stillness stranger strength struggle submission surprise surrender teaching
tears temptation thanksgiving thirst thought time tiredness tolerance tradition transformation
treasure trial turning uncertainty understanding unity urgency vanity vision vulnerability
waiting wakefulness wandering weakness welcome will wisdom witness wonder work worship worth
yearning zeal acceptance attention betrayal blessing brokenness childhood choice consecration
cross debt ecstasy exile fire flesh gift glory habit heart heaven hell honor hunger
imitation incarnation joy kingdom knowledge labor loss love loyalty lying margin marriage
mercy mind mission money morning mystery naming nature neighbor night obedience offering
openness ordinariness pain patience peacemaking persecution persistence place play pleasure
poverty power praise prayer presence pride promise prophecy protection provision purity
purpose question quiet rage readiness rebellion reconciliation redemption regret release
remembrance renewal repentance resilience resistance rest restoration resurrection revelation
reverence reward rhythm righteousness ritual sacrifice sadness safety sanctification
scarcity scripture secrecy security seeker self service shame silence simplicity sin sleep
slowness sorrow soul speech spirit stability stewardship stillness stranger strength struggle
submission suffering surprise surrender teaching tears temptation thanksgiving thirst thought
time tiredness tolerance tradition transformation treasure trial trust truth turning
uncertainty understanding unity urgency vanity vision vulnerability waiting wakefulness
wandering weakness wealth welcome will wisdom witness wonder work worship worth yearning zeal
beginning ending renewal morning evening winter spring summer autumn path gate door bread
water wine light shadow seed field harvest shepherd vine fig mountain sea storm calm bread
cup cross crown thorn robe veil temple altar covenant exile return home stranger pilgrim
sojourner witness martyr saint sinner prodigal elder child widow orphan foreigner neighbor
enemy friend brother sister mother father son daughter servant master teacher student
healing wound scar memory forgetting dream vision nightmare sleep waking vigil fasting feast
hunger thirst satisfaction emptiness fullness measure balance weight yoke burden gift talent
parable miracle sign wonder ordinary extraordinary silence speech word voice listening
hearing seeing blindness insight confusion wisdom folly knowledge ignorance learning
unlearning doubt certainty risk safety courage fear peace conflict resolution anger
forgiveness bitterness sweetness hardness softness strength weakness powerlessness authority
humiliation exaltation lowliness greatness smallness breadth narrowness wide path strait
gate stumbling block cornerstone foundation rock sand storm shelter refuge fortress tower
city wilderness garden desert river flood dryness rain cloud sunshine eclipse dawn dusk
noon midnight hour moment season time eternity patience impatience waiting hastening delay
""".split()

def main() -> None:
    seen: set[str] = set()
    themes: list[str] = []
    for t in ORIGINAL_30 + SUPPLEMENT:
        k = t.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        # preserve original casing from first occurrence
        themes.append(t.strip())
        if len(themes) >= 366:
            break

    if len(themes) < 366:
        n = len(themes)
        raise SystemExit(f"Need 366 unique themes, only have {n}. Add more to SUPPLEMENT.")

    themes = themes[:366]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"themes": themes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(themes)} themes to {OUT}")


if __name__ == "__main__":
    main()
