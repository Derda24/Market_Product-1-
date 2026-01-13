#!/usr/bin/env python3
"""
Nutrition enricher for Barcelona_scraper products.

Fetches nutrition and health score data from OpenFoodFacts for products that
are missing entries in the Supabase `nutrition_data` table. The script uses
fuzzy matching to select the best OpenFoodFacts candidate, applies a
NutriScore-to-health-score conversion, and upserts the results back into
Supabase.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Dict, Generator, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from supabase import Client, create_client

LOGGER = logging.getLogger("nutrition_enricher")

OPENFOODFACTS_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OPENFOODFACTS_PAGE_SIZE = 20
DEFAULT_MIN_MATCH_SCORE = 72
DEFAULT_REQUEST_DELAY = 0.8
MAX_RETRIES = 3

NUTRISCORE_HEALTH_MAP = {
    "a": 95,
    "b": 85,
    "c": 70,
    "d": 55,
    "e": 40,
}


@dataclass
class Product:
    id: str
    name: str
    category: Optional[str]
    store_id: Optional[str]
    quantity: Optional[str]


@dataclass
class NutritionMatch:
    product: Dict
    score: float
    candidate_name: str


def configure_logging(verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    )

    file_handler = logging.FileHandler("nutrition_enrichment.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )

    LOGGER.handlers.clear()
    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(file_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign health scores to Supabase products using OpenFoodFacts."
    )
    parser.add_argument(
        "--store",
        help="Only process products for a specific store_id.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many products.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=DEFAULT_MIN_MATCH_SCORE,
        help="Minimum fuzzy match score (0-100) required to accept a result.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help="Delay (seconds) between OpenFoodFacts requests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch nutrition data but do not write back to Supabase.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging."
    )
    return parser.parse_args()


def load_supabase_client() -> Client:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_service_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be defined in the environment."
        )
    return create_client(supabase_url, supabase_service_key)


def normalize_product_name(name: str) -> str:
    """Normalize a product name to improve matching accuracy."""
    cleaned = name.lower()
    store_tokens = [
        "el corte inglés",
        "carrefour",
        "mercadona",
        "alcampo",
        "eroski",
        "bonpreu",
        "condis",
        "dia",
        "lidl",
        "aldi",
        "bonarea",
        "caprabo",
    ]
    for token in store_tokens:
        cleaned = cleaned.replace(token, " ")

    # Remove explicit quantity expressions (e.g., "3 x 200 ml", "500g", "1 l")
    cleaned = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:x\s*)?\d*(?:[.,]\d+)?\s*(?:kg|g|mg|l|ml|cl|unidades|unidad|uds|u|pack)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:kg|g|mg|l|ml|cl)\b", " ", cleaned)

    cleaned = " ".join(cleaned.split())
    return cleaned


def parse_float(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_health_score(
    grade: Optional[str], score_fr: Optional[float]
) -> Optional[int]:
    if grade:
        grade = grade.lower()
        mapped = NUTRISCORE_HEALTH_MAP.get(grade)
        if mapped is not None:
            return mapped

    if score_fr is not None:
        # OpenFoodFacts scores range roughly from -15 (best) to +40 (worst)
        scaled = 100 - ((score_fr + 15) * (100 / 55))
        return int(max(0, min(100, round(scaled))))

    return None


def extract_grade(product_data: Dict) -> Optional[str]:
    grade_candidates = [
        product_data.get("nutriscore_grade"),
        product_data.get("nutrition_grades"),
        product_data.get("nutrition_grade_fr"),
    ]
    for candidate in grade_candidates:
        if isinstance(candidate, list) and candidate:
            return str(candidate[0]).lower()
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return None


def build_candidate_name(product_data: Dict) -> Optional[str]:
    fields = [
        product_data.get("product_name_es"),
        product_data.get("product_name"),
        product_data.get("generic_name_es"),
        product_data.get("generic_name"),
        product_data.get("brands"),
    ]
    parts: List[str] = []
    for field in fields:
        if not field:
            continue
        if isinstance(field, str):
            parts.append(field)
        elif isinstance(field, list):
            parts.extend(field)
    candidate = " ".join(part.strip() for part in parts if part and str(part).strip())
    candidate = candidate.strip()
    return candidate or None


class OpenFoodFactsClient:
    def __init__(self, min_match_score: int, request_delay: float) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "BarcelonaScraperNutrition/1.0 (+https://github.com/)",
                "Accept": "application/json",
            }
        )
        self.min_match_score = min_match_score
        self.request_delay = request_delay

    def search(self, term: str) -> List[Dict]:
        params = {
            "search_terms": term,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": OPENFOODFACTS_PAGE_SIZE,
            "fields": ",".join(
                [
                    "id",
                    "code",
                    "brands",
                    "product_name",
                    "product_name_es",
                    "generic_name",
                    "generic_name_es",
                    "nutriscore_grade",
                    "nutrition_grades",
                    "nutrition_grade_fr",
                    "nutriments",
                ]
            ),
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(
                    OPENFOODFACTS_SEARCH_URL, params=params, timeout=15
                )
                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", attempt + 1))
                    LOGGER.warning("OpenFoodFacts rate-limited; sleeping for %ss", wait)
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                return data.get("products", []) or []
            except requests.RequestException as exc:
                delay = 2**attempt
                LOGGER.warning(
                    "OpenFoodFacts request failed (%s). Retrying in %ss.",
                    exc,
                    delay,
                )
                time.sleep(delay)
        return []

    def find_best_match(self, product: Product) -> Optional[NutritionMatch]:
        search_terms = [product.name]
        normalized = normalize_product_name(product.name)
        if normalized != product.name.lower():
            search_terms.append(normalized)

        if product.quantity and product.quantity not in product.name:
            search_terms.append(f"{product.name} {product.quantity}")

        seen_terms = set()
        for term in search_terms:
            clean_term = " ".join(term.split())
            if not clean_term or clean_term.lower() in seen_terms:
                continue
            seen_terms.add(clean_term.lower())

            LOGGER.debug("Searching OpenFoodFacts for '%s'", clean_term)
            products = self.search(clean_term)
            if not products:
                LOGGER.debug("No OpenFoodFacts results for '%s'", clean_term)
                continue

            match = self._pick_best_candidate(product, products)
            if match:
                # Respect rate limiting even on success
                time.sleep(self.request_delay)
                return match

            time.sleep(self.request_delay)

        return None

    def _pick_best_candidate(
        self, product: Product, candidates: Iterable[Dict]
    ) -> Optional[NutritionMatch]:
        candidate_wrappers: List[Tuple[str, Dict]] = []
        for candidate in candidates:
            candidate_name = build_candidate_name(candidate)
            if not candidate_name:
                continue
            candidate_wrappers.append((candidate_name, candidate))

        if not candidate_wrappers:
            return None

        normalized_query = normalize_product_name(product.name)
        match = process.extractOne(
            normalized_query,
            candidate_wrappers,
            processor=lambda item: normalize_product_name(item[0]),
            scorer=fuzz.WRatio,
            score_cutoff=self.min_match_score,
        )
        if not match:
            return None

        (candidate_name, candidate_data), score, _ = match
        LOGGER.info(
            "Matched '%s' (score %.1f) with OpenFoodFacts '%s'",
            product.name,
            score,
            candidate_name,
        )
        return NutritionMatch(
            product=candidate_data, score=score, candidate_name=candidate_name
        )


class NutritionEnricher:
    def __init__(
        self,
        supabase: Client,
        off_client: OpenFoodFactsClient,
        dry_run: bool = False,
        store_filter: Optional[str] = None,
    ) -> None:
        self.supabase = supabase
        self.off_client = off_client
        self.dry_run = dry_run
        self.store_filter = store_filter
        self.existing_nutrition = self._load_existing_nutrition()

    def _load_existing_nutrition(self) -> Dict[str, Optional[int]]:
        LOGGER.debug("Fetching existing nutrition_data entries from Supabase")
        nutrition_map: Dict[str, Optional[int]] = {}
        start = 0
        batch_size = 500

        while True:
            response = (
                self.supabase.table("nutrition_data")
                .select("product_id, health_score")
                .range(start, start + batch_size - 1)
                .execute()
            )
            rows = response.data or []
            LOGGER.debug("Fetched %d nutrition_data rows (offset %d)", len(rows), start)
            for row in rows:
                nutrition_map[row["product_id"]] = row.get("health_score")

            if len(rows) < batch_size:
                break
            start += batch_size

        LOGGER.info(
            "Loaded %d existing nutrition entries from Supabase", len(nutrition_map)
        )
        return nutrition_map

    def iter_products_missing_health(self) -> Generator[Product, None, None]:
        LOGGER.debug("Fetching products missing health scores")
        start = 0
        batch_size = 200

        while True:
            query = (
                self.supabase.table("products")
                .select("id, name, category, store_id, quantity")
                .order("created_at", desc=False)
                .range(start, start + batch_size - 1)
            )

            if self.store_filter:
                query = query.eq("store_id", self.store_filter)

            response = query.execute()
            rows = response.data or []

            if not rows:
                break

            LOGGER.debug("Fetched %d products (offset %d)", len(rows), start)
            for row in rows:
                product_id = row["id"]
                health_score = self.existing_nutrition.get(product_id)
                if health_score is None:
                    yield Product(
                        id=product_id,
                        name=row["name"],
                        category=row.get("category"),
                        store_id=row.get("store_id"),
                        quantity=row.get("quantity"),
                    )

            if len(rows) < batch_size:
                break
            start += batch_size

    def upsert_nutrition(
        self, product_id: str, nutrition_score: str, health_score: Optional[int]
    ) -> None:
        payload = {
            "product_id": product_id,
            "nutrition_score": nutrition_score,
            "health_score": health_score,
        }
        if self.dry_run:
            LOGGER.info("[dry-run] Would upsert nutrition: %s", payload)
            return

        LOGGER.debug("Upserting nutrition data for %s", product_id)
        response = self.supabase.table("nutrition_data").upsert(payload).execute()
        if response.data is None:
            LOGGER.debug("Supabase upsert response: %s", response)
        self.existing_nutrition[product_id] = health_score

    def process_product(self, product: Product) -> bool:
        LOGGER.info("Processing product: %s (%s)", product.name, product.id)
        match = self.off_client.find_best_match(product)
        if not match:
            LOGGER.warning("No OpenFoodFacts match found for '%s'", product.name)
            return False

        grade = extract_grade(match.product)
        nutriments = match.product.get("nutriments") or {}
        score_fr = parse_float(
            nutriments.get("nutrition_score_fr")
            or nutriments.get("nutrition-score-fr")
            or nutriments.get("nutrition-score-fr_100g")
        )
        health_score = compute_health_score(grade, score_fr)
        nutrition_score = grade or "unknown"

        if health_score is None:
            LOGGER.warning(
                "OpenFoodFacts match lacked health score data: %s", match.candidate_name
            )

        self.upsert_nutrition(product.id, nutrition_score, health_score)
        return health_score is not None

    def run(self, limit: Optional[int] = None) -> Dict[str, int]:
        stats = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }

        for product in self.iter_products_missing_health():
            if limit is not None and stats["processed"] >= limit:
                LOGGER.info("Reached processing limit (%d)", limit)
                break

            stats["processed"] += 1
            try:
                success = self.process_product(product)
                if success:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:  # noqa: BLE001 - top-level processing guard
                LOGGER.exception("Failed to process '%s': %s", product.name, exc)
                stats["failed"] += 1

        LOGGER.info(
            "Nutrition enrichment complete: processed=%(processed)d, updated=%(updated)d, "
            "skipped=%(skipped)d, failed=%(failed)d",
            stats,
        )
        return stats


def main() -> None:
    args = parse_args()
    configure_logging(verbose=args.verbose)

    try:
        supabase_client = load_supabase_client()
    except Exception as exc:  # noqa: BLE001 - config errors should exit gracefully
        LOGGER.error("Failed to initialise Supabase client: %s", exc)
        sys.exit(1)

    off_client = OpenFoodFactsClient(
        min_match_score=args.min_score, request_delay=args.delay
    )
    enricher = NutritionEnricher(
        supabase=supabase_client,
        off_client=off_client,
        dry_run=args.dry_run,
        store_filter=args.store,
    )

    stats = enricher.run(limit=args.limit)

    # Make CLI-friendly exit codes
    if stats["failed"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

