from aii.models.ibcf import IBCFRecommender, ModelConfig

cfg = ModelConfig(processed_dir="aii/data/processed")
model = IBCFRecommender(cfg)
model.load()
model.load_or_fit()

recs = model.recommend(user_id=1, limit=5)
for r in recs:
    print(r)
