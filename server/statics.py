import os


ROOT = os.path.dirname(__file__)
ROOT = os.path.join(ROOT, "..")

CAPTURES_DIR = os.path.join(ROOT, "captures")
EXPERIMENTS_DIR = os.path.join(ROOT, "experiment")
LOG_DIR = os.path.join(ROOT, "logs")

PLAYER_DIR = os.path.join(ROOT, "client", "player")
STATIC_DIR = os.path.join(ROOT, "client", "static")
MODELS_DIR = os.path.join(ROOT, "models")
DASH_DIR = os.path.join(ROOT, "dash")

PREVIEW_CANDIDATES = ("preview.png", "preview.jpg")

EVICT_AFTER_MS = 10 * 60_000
EVICT_CHECK_EVERY_S = 20