from src.config import MODEL_PATH, THRESHOLD_PATH, DEFAULT_THRESHOLD, WINDOW_SIZE

MIN_CONSECUTIVE = 3

RULE_WINDOW_SIZE = 12
RULE_MIN_LOSS = 15.0
RULE_RECOVERY_WINDOW = 288   # 24 h à raison d'une mesure toutes les 5 minutes
RULE_RECOVERY_TOL = 0.3
RULE_FILTER_WINDOW = 13      # ~1 h pour neutraliser les plateaux parasites courts
RULE_OSCILLATION_STEP = 1.0
RULE_MAX_SIGN_CHANGES = 3
RULE_OSCILLATION_LOOKAHEAD = 6
RULE_LOCAL_OSCILLATION_WINDOW = 60
RULE_LOCAL_OSCILLATION_AMPLITUDE = 30.0
RULE_LOCAL_OSCILLATION_RETURN_TOL = 10.0
RULE_OPPOSITE_RETURN_TOL = 10.0
RULE_PERSISTENT_STEP_MIN_LOSS = 50.0
GATE_LOSS_MULTIPLIER = 2.5
MIN_SCALE_FLOOR = 1.0
MIN_STATE_ROWS = 10           # nb minimal de lignes dans CHAQUE état pour juger le statut exploitable
SCALE_PERCENTILE_LOW = 90     # peu d'échantillons : limite la contamination par l'anomalie elle-même
SCALE_PERCENTILE_HIGH = 97    # beaucoup d'échantillons : tolère les sites naturellement bruyants
MIN_SAMPLES_FOR_HIGH_PERCENTILE = 100
GLITCH_REFERENCE_FRACTION = 0.3  # une coupure est confirmée si le niveau voisin dépasse 30% du P95

# Vol masqué par une chute à 0 : niveau avant la coupure > niveau stable après la coupure
ZERO_BRIDGE_BEFORE_ROWS = 6        # relevés avant la coupure pour estimer le niveau de départ
ZERO_BRIDGE_AFTER_ROWS = 12        # ~1 h de relevés stables exigés après la coupure
ZERO_BRIDGE_STABLE_TOL = 5.0       # litres : écart max toléré sur ces relevés (ou 20 % de la perte)
ZERO_BRIDGE_MAX_GAP_UNRELIABLE = 36  # sans statut fiable : coupures de 3 h maximum

# Constantes conservées pour compatibilité (plus utilisées par la logique actuelle)
RULE_DROP_MULTIPLIER = 5
RULE_FILE_OSCILLATION_DEVIATION = 15.0
RULE_FILE_OSCILLATION_BASELINE_TOL = 10.0

_CHUNK = 50_000  # taille de bloc pour les calculs vectorisés gourmands en mémoire


# ---------------------------------------------------------------------------
# Chargement du modèle (mis en cache, rechargé automatiquement si le .pkl change)
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Outils génériques
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Statut du générateur
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Coupures capteur (relevés figés à 0)
# ---------------------------------------------------------------------------











# ---------------------------------------------------------------------------
# Échelles de bruit / consommation propres au site
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# Masques de suppression / confirmation
# ---------------------------------------------------------------------------









# ---------------------------------------------------------------------------
# Règle principale
# ---------------------------------------------------------------------------

















# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

from src.predict_model_utils import load_model
from src.predict_generic_utils import _smooth
from src.predict_status_utils import parse_status
from src.predict_glitch_utils import confirmed_glitch_mask
from src.predict_bridge_utils import zero_bridged_losses_for
from src.predict_pipeline_utils import predict, predict_arrays
