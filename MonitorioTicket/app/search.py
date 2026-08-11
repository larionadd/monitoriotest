from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    source: str
    route: str
    price: int
    currency: str
    depart_date: str
    is_exact_date: bool
    is_requested_airport: bool
    stops: int
    baggage_included: bool


def score_candidate(candidate: Candidate) -> int:
    score = candidate.price
    if not candidate.is_exact_date:
        score += 25
    if not candidate.is_requested_airport:
        score += 40
    if candidate.stops > 0:
        score += 35 * candidate.stops
    if not candidate.baggage_included:
        score += 20
    return score


def rank_candidates(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=score_candidate)


def source_order() -> list[str]:
    return [
        "live_flights_if_available",
        "travelpayouts_cached_prices",
        "flexible_date_expansion",
        "nearby_departure_city_expansion",
        "tour_partners_after_mvp",
        "direct_airline_scraping_research_only",
    ]
