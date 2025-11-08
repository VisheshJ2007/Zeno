"""
FSRS (Free Spaced Repetition Scheduler) Algorithm Implementation
Based on FSRS v4 specification

FSRS is a modern spaced repetition algorithm that models memory more accurately than SM-2.
It uses stability and difficulty parameters to predict optimal review intervals.
"""

import math
from typing import Tuple, Dict, List
from datetime import datetime, timedelta
from enum import Enum


class Rating(Enum):
    """Review ratings"""
    AGAIN = 1  # Complete forget, need to relearn
    HARD = 2   # Remembered with significant difficulty
    GOOD = 3   # Remembered correctly
    EASY = 4   # Remembered easily and quickly


class State(Enum):
    """Card states"""
    NEW = "new"           # Never reviewed
    LEARNING = "learning" # Initial learning phase
    REVIEW = "review"     # In review phase with stable memory
    RELEARNING = "relearning"  # Forgotten, relearning


class FSRSParameters:
    """
    FSRS algorithm parameters
    These are global parameters that can be tuned per student or course
    """
    def __init__(self):
        # Default parameters (optimized from research)
        self.w = [
            0.4,     # w0: initial stability for Again
            0.6,     # w1: initial stability for Hard
            2.4,     # w2: initial stability for Good
            5.8,     # w3: initial stability for Easy
            4.93,    # w4: stability increase factor for Again
            0.94,    # w5: stability increase factor for Hard
            0.86,    # w6: stability increase factor for Good
            0.01,    # w7: stability increase factor for Easy
            1.49,    # w8: difficulty increase factor for Again
            0.14,    # w9: difficulty decrease factor for Easy
            0.94,    # w10: difficulty baseline
            2.18,    # w11: difficulty factor
            0.05,    # w12: stability factor
            0.34,    # w13: difficulty penalty
            1.26,    # w14: stability bonus
            0.29,    # w15: difficulty bonus
            2.61,    # w16: stability decay factor
        ]

        # Initial stability for new cards (in days)
        self.initial_stability = {
            Rating.AGAIN: self.w[0],
            Rating.HARD: self.w[1],
            Rating.GOOD: self.w[2],
            Rating.EASY: self.w[3]
        }

        # Initial difficulty for new cards (1-10 scale)
        self.initial_difficulty = 5.0

        # Retention target (90% = 0.9)
        self.request_retention = 0.9

        # Maximum interval in days
        self.maximum_interval = 36500  # ~100 years

        # Factor for converting stability to interval
        self.factor = 0.9 ** (1 / self.request_retention) - 1


class FSRSCard:
    """Represents a card's FSRS state"""

    def __init__(
        self,
        stability: float = 0.0,
        difficulty: float = 5.0,
        elapsed_days: float = 0.0,
        scheduled_days: float = 0.0,
        reps: int = 0,
        lapses: int = 0,
        state: State = State.NEW,
        last_review: datetime = None
    ):
        self.stability = stability
        self.difficulty = difficulty
        self.elapsed_days = elapsed_days
        self.scheduled_days = scheduled_days
        self.reps = reps
        self.lapses = lapses
        self.state = state
        self.last_review = last_review or datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "stability": self.stability,
            "difficulty": self.difficulty,
            "elapsed_days": self.elapsed_days,
            "scheduled_days": self.scheduled_days,
            "reps": self.reps,
            "lapses": self.lapses,
            "state": self.state.value,
            "last_review": self.last_review
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FSRSCard":
        """Create from dictionary"""
        return cls(
            stability=data.get("stability", 0.0),
            difficulty=data.get("difficulty", 5.0),
            elapsed_days=data.get("elapsed_days", 0.0),
            scheduled_days=data.get("scheduled_days", 0.0),
            reps=data.get("reps", 0),
            lapses=data.get("lapses", 0),
            state=State(data.get("state", "new")),
            last_review=data.get("last_review")
        )


class FSRSScheduler:
    """
    FSRS Scheduler - calculates next review dates based on performance
    """

    def __init__(self, params: FSRSParameters = None):
        self.params = params or FSRSParameters()

    def _calculate_interval(self, stability: float) -> float:
        """
        Calculate interval from stability
        Interval = Stability × (R^(1/D) - 1) / Factor
        where R = request retention, D = decay rate
        """
        return max(1.0, stability * self.params.factor)

    def _mean_reversion(self, init: float, current: float) -> float:
        """Apply mean reversion to prevent extreme values"""
        return self.params.w[10] * init + (1 - self.params.w[10]) * current

    def _next_difficulty(self, difficulty: float, rating: Rating) -> float:
        """Calculate next difficulty based on rating"""
        delta = rating.value - 3  # -2, -1, 0, 1

        next_d = difficulty + self.params.w[8] * delta

        # Apply mean reversion
        next_d = self._mean_reversion(self.params.initial_difficulty, next_d)

        # Clamp to valid range [1, 10]
        return max(1.0, min(10.0, next_d))

    def _next_stability(
        self,
        current_stability: float,
        difficulty: float,
        rating: Rating,
        elapsed_days: float
    ) -> float:
        """Calculate next stability based on rating and forgetting curve"""

        if current_stability == 0:
            # New card - use initial stability
            return self.params.initial_stability[rating]

        # Calculate retrievability (probability of recall)
        retrievability = math.exp(
            math.log(0.9) * elapsed_days / current_stability
        )

        # Stability increase depends on rating
        if rating == Rating.AGAIN:
            # Card forgotten - reset stability with penalty
            new_s = current_stability * math.exp(
                self.params.w[4] * (difficulty - 5) * self.params.w[12]
            )
        elif rating == Rating.HARD:
            # Barely remembered - modest increase
            new_s = current_stability * (
                1 + math.exp(self.params.w[5]) *
                (difficulty - 5) *
                self.params.w[13] *
                (1 - retrievability)
            )
        elif rating == Rating.GOOD:
            # Remembered well - good increase
            new_s = current_stability * (
                1 + math.exp(self.params.w[6]) *
                (11 - difficulty) *
                self.params.w[14] *
                (1 - retrievability)
            )
        else:  # EASY
            # Remembered easily - maximum increase
            new_s = current_stability * (
                1 + math.exp(self.params.w[7]) *
                (11 - difficulty) *
                self.params.w[15] *
                (1 - retrievability)
            )

        return max(0.1, min(self.params.maximum_interval, new_s))

    def _next_state(self, current_state: State, rating: Rating) -> State:
        """Determine next state based on current state and rating"""

        if current_state == State.NEW:
            if rating == Rating.AGAIN:
                return State.LEARNING
            else:
                return State.REVIEW

        elif current_state == State.LEARNING:
            if rating == Rating.AGAIN:
                return State.LEARNING
            else:
                return State.REVIEW

        elif current_state == State.REVIEW:
            if rating == Rating.AGAIN:
                return State.RELEARNING
            else:
                return State.REVIEW

        else:  # RELEARNING
            if rating == Rating.AGAIN:
                return State.RELEARNING
            else:
                return State.REVIEW

    def review_card(
        self,
        card: FSRSCard,
        rating: Rating,
        review_time: datetime = None
    ) -> Tuple[FSRSCard, datetime]:
        """
        Process a card review and return updated card + next review date

        Args:
            card: Current card state
            rating: Review rating (1-4)
            review_time: When the review happened (default: now)

        Returns:
            (updated_card, next_review_date)
        """

        if review_time is None:
            review_time = datetime.utcnow()

        # Calculate elapsed days since last review
        if card.last_review:
            elapsed_days = (review_time - card.last_review).total_seconds() / 86400
        else:
            elapsed_days = 0.0

        # Calculate next difficulty
        next_difficulty = self._next_difficulty(card.difficulty, rating)

        # Calculate next stability
        next_stability = self._next_stability(
            card.stability,
            card.difficulty,
            rating,
            elapsed_days if elapsed_days > 0 else card.scheduled_days
        )

        # Calculate next interval
        next_interval = self._calculate_interval(next_stability)

        # Determine next state
        next_state = self._next_state(card.state, rating)

        # Update counters
        next_reps = card.reps + 1
        next_lapses = card.lapses + (1 if rating == Rating.AGAIN else 0)

        # Create updated card
        updated_card = FSRSCard(
            stability=next_stability,
            difficulty=next_difficulty,
            elapsed_days=elapsed_days,
            scheduled_days=next_interval,
            reps=next_reps,
            lapses=next_lapses,
            state=next_state,
            last_review=review_time
        )

        # Calculate next review date
        next_review_date = review_time + timedelta(days=next_interval)

        return updated_card, next_review_date

    def get_retrievability(self, card: FSRSCard, now: datetime = None) -> float:
        """
        Calculate current retrievability (probability of recall)

        Args:
            card: Card to check
            now: Current time (default: now)

        Returns:
            Retrievability (0.0 to 1.0)
        """
        if now is None:
            now = datetime.utcnow()

        if card.stability == 0 or card.last_review is None:
            return 1.0  # New card

        elapsed_days = (now - card.last_review).total_seconds() / 86400

        # Exponential forgetting curve
        retrievability = math.exp(
            math.log(self.params.request_retention) * elapsed_days / card.stability
        )

        return max(0.0, min(1.0, retrievability))

    def is_due(self, card: FSRSCard, now: datetime = None) -> bool:
        """Check if a card is due for review"""
        if now is None:
            now = datetime.utcnow()

        if card.state == State.NEW:
            return True

        if card.last_review is None:
            return True

        next_review = card.last_review + timedelta(days=card.scheduled_days)
        return now >= next_review

    def get_next_review_date(self, card: FSRSCard) -> datetime:
        """Get the next scheduled review date"""
        if card.last_review is None:
            return datetime.utcnow()

        return card.last_review + timedelta(days=card.scheduled_days)


# ============================================================================
# Utility Functions
# ============================================================================

def create_new_card() -> FSRSCard:
    """Create a new card with default FSRS parameters"""
    return FSRSCard(
        stability=0.0,
        difficulty=5.0,
        elapsed_days=0.0,
        scheduled_days=0.0,
        reps=0,
        lapses=0,
        state=State.NEW,
        last_review=None
    )


def rating_from_int(value: int) -> Rating:
    """Convert integer (1-4) to Rating enum"""
    mapping = {
        1: Rating.AGAIN,
        2: Rating.HARD,
        3: Rating.GOOD,
        4: Rating.EASY
    }
    return mapping.get(value, Rating.GOOD)


# Example usage and testing
if __name__ == "__main__":
    # Create scheduler
    scheduler = FSRSScheduler()

    # Create new card
    card = create_new_card()
    print(f"New card: State={card.state.value}, Difficulty={card.difficulty}")

    # First review - rated as GOOD
    card, next_date = scheduler.review_card(card, Rating.GOOD)
    print(f"\nAfter GOOD review:")
    print(f"  State: {card.state.value}")
    print(f"  Stability: {card.stability:.2f} days")
    print(f"  Difficulty: {card.difficulty:.2f}")
    print(f"  Next review: {next_date}")
    print(f"  Interval: {card.scheduled_days:.2f} days")

    # Simulate review after interval
    card.last_review = next_date
    card, next_date = scheduler.review_card(card, Rating.GOOD)
    print(f"\nAfter second GOOD review:")
    print(f"  Stability: {card.stability:.2f} days")
    print(f"  Next review: {next_date}")
    print(f"  Interval: {card.scheduled_days:.2f} days")

    # Simulate forgetting
    card.last_review = next_date
    card, next_date = scheduler.review_card(card, Rating.AGAIN)
    print(f"\nAfter AGAIN (forgot):")
    print(f"  State: {card.state.value}")
    print(f"  Stability: {card.stability:.2f} days")
    print(f"  Lapses: {card.lapses}")
    print(f"  Next review: {next_date}")
