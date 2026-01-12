# Baseline model training entry-point
from aii.models.ibcf import IBCFRecommender, ModelConfig

def train() -> None:
    """
    Entry-point for training the baseline recommender.
    The actual training logic is implemented inside the model.
    """
    cfg = ModelConfig()
    model = IBCFRecommender(cfg)
    model.load()
    model.load_or_fit()
