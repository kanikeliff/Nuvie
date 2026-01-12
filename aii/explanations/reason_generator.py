from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


# ============================================================
# Input structure for explanation generation
# ============================================================
# This object contains everything needed to explain
# *why* a movie was recommended to a user.
# ============================================================

@dataclass(frozen=True)
class ReasonInput:
    # ID of the user receiving the recommendation
    user_id: int

    # ID of the recommended movie
    rec_movie_id: int

    # ID of a previously liked movie that influenced this recommendation
    # (can be None for cold-start or popularity-based recommendations)
    seed_movie_id: Optional[int]

    # Mapping: movie_id -> movie title
    movie_title: Dict[int, str]

    # Mapping: movie_id -> set of genres
    movie_genres: Dict[int, Set[str]]

    # Whether social signals should be used in explanation
    use_social: bool = False

    # Optional list of friend IDs (used only when social explanations are enabled)
    friend_ids: Optional[List[int]] = None


# ============================================================
# Explanation generator
# ============================================================
# This function selects the most appropriate explanation
# based on available signals:
#   1) social influence
#   2) genre overlap
#   3) similarity to previously rated movie
#   4) popularity (fallback)
# ============================================================

def generate_reason(inp: ReasonInput) -> Dict:
    # Resolve movie titles (safe fallback text if missing)
    rec_title = inp.movie_title.get(inp.rec_movie_id, "this movie")
    seed_title = (
        inp.movie_title.get(inp.seed_movie_id, "a movie you liked")
        if inp.seed_movie_id
        else None
    )

    # Get genre sets for recommended and seed movies
    rec_g = inp.movie_genres.get(inp.rec_movie_id, set())
    seed_g = inp.movie_genres.get(inp.seed_movie_id, set()) if inp.seed_movie_id else set()

    # Find overlapping genres (used for explanation)
    overlap = sorted(rec_g & seed_g)

    # --------------------------------------------------------
    # Case 1: Social-based explanation
    # --------------------------------------------------------
    if inp.use_social:
        return {
            "primary_reason": "social",
            "confidence": 0.70,
            "text": "Popular with people you follow, and similar to your taste.",
            "factors": [
                {
                    "type": "social",
                    "weight": 0.6,
                    "payload": {"friend_ids": inp.friend_ids or []},
                },
                {
                    "type": "genre_overlap",
                    "weight": 0.4,
                    "payload": {"overlap": overlap[:3]},
                },
            ],
        }

    # --------------------------------------------------------
    # Case 2: Genre overlap with a previously liked movie
    # --------------------------------------------------------
    if inp.seed_movie_id and overlap:
        return {
            "primary_reason": "genre_overlap",
            "confidence": 0.78,
            "text": (
                f"Because you liked {seed_title} and it shares genres: "
                f"{', '.join(overlap[:3])}."
            ),
            "factors": [
                {
                    "type": "because_you_rated",
                    "weight": 0.6,
                    "payload": {"seed_movie_id": int(inp.seed_movie_id)},
                },
                {
                    "type": "genre_overlap",
                    "weight": 0.4,
                    "payload": {"overlap": overlap[:3]},
                },
            ],
        }

    # --------------------------------------------------------
    # Case 3: Similarity-based explanation (no explicit genre overlap)
    # --------------------------------------------------------
    if inp.seed_movie_id:
        return {
            "primary_reason": "because_you_rated",
            "confidence": 0.75,
            "text": f"Because you liked {seed_title}, which is similar to {rec_title}.",
            "factors": [
                {
                    "type": "because_you_rated",
                    "weight": 1.0,
                    "payload": {"seed_movie_id": int(inp.seed_movie_id)},
                },
            ],
        }

    # --------------------------------------------------------
    # Case 4: Popularity-based fallback (cold-start)
    # --------------------------------------------------------
    return {
        "primary_reason": "popular",
        "confidence": 0.60,
        "text": f"Recommended because {rec_title} is popular among users.",
        "factors": [
            {"type": "popular", "weight": 1.0, "payload": {}}
        ],
    }
