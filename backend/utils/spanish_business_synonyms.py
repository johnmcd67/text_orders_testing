"""
Spanish Business Name Synonyms and Patterns

Centralized dictionary of Spanish business term synonyms, legal entity patterns,
and buying group keywords for improved fuzzy matching of customer names.
"""

import re

# Business type synonyms (normalize to canonical form)
# Key: synonym to replace, Value: canonical form to normalize to
BUSINESS_TYPE_SYNONYMS = {
    # Building supplies synonyms
    "almacenes": "materiales",
    "almacen": "materiales",
    "suministros": "materiales",

    # Distributor variations
    "distribuciones": "distribuidor",
    "distribuidora": "distribuidor",

    # Construction variations
    "construcciones": "construccion",

    # Commerce variations
    "comercial": "comercio",
}

# Legal entity suffix patterns (regex pattern, replacement)
# These patterns normalize Spanish legal entity suffixes to standard forms
LEGAL_ENTITY_PATTERNS = [
    # Sociedad Limitada variations (with and without trailing period)
    (r'\bS\.L\.U\.?\b', 'SL'),  # S.L.U. or S.L.U -> SL
    (r'\bS\.L\.?\b', 'SL'),     # S.L. or S.L -> SL (catches most cases)
    (r'\b,\s*S\.L\.?\b', ' SL'),  # , S.L. or , S.L -> SL

    # Sociedad Anónima variations
    (r'\bS\.A\.?\b', 'SA'),     # S.A. or S.A -> SA
    (r'\b,\s*S\.A\.?\b', ' SA'),  # , S.A. or , S.A -> SA

    # Sociedad Cooperativa
    (r'\bS\.C\.?\b', 'SC'),     # S.C. or S.C -> SC

    # Sociedad Limitada Laboral
    (r'\bS\.L\.L\.?\b', 'SL'),  # S.L.L. or S.L.L -> SL
]

# Pre-compile regex patterns for performance
COMPILED_LEGAL_ENTITY_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in LEGAL_ENTITY_PATTERNS
]

# Buying group keywords (for score boosting)
# These keywords indicate buying group membership and should boost match scores
BUYING_GROUP_KEYWORDS = [
    "gamma",
    "gremio",
    "grupo",
    "cadena",
    "asociacion",
]

# Spanish gendered name pairs (normalize masculine <-> feminine for fuzzy matching)
# This allows fuzzy matching to recognize ANTONIO and ANTONIA as equivalent
SPANISH_GENDERED_NAMES = {
    # Masculine -> Feminine
    "antonio": "antonia",
    "francisco": "francisca",
    "jose": "josefa",
    "juan": "juana",
    "carlos": "carla",
    "daniel": "daniela",
    "pablo": "paula",
    "angel": "angela",
    "manuel": "manuela",
    "andres": "andrea",
    "mario": "maria",
    "alejandro": "alejandra",
    "roberto": "roberta",
    "alberto": "alberta",
    "fernando": "fernanda",
    "luis": "luisa",
    "miguel": "miguela",
    "rafael": "rafaela",
    "sergio": "sergia",
    "diego": "diega",

    # Feminine -> Masculine (reverse mappings for bidirectional matching)
    "antonia": "antonio",
    "francisca": "francisco",
    "josefa": "jose",
    "juana": "juan",
    "carla": "carlos",
    "daniela": "daniel",
    "paula": "pablo",
    "angela": "angel",
    "manuela": "manuel",
    "andrea": "andres",
    "maria": "mario",
    "alejandra": "alejandro",
    "roberta": "roberto",
    "alberta": "alberto",
    "fernanda": "fernando",
    "luisa": "luis",
    "miguela": "miguel",
    "rafaela": "rafael",
    "sergia": "sergio",
    "diega": "diego",
}

# Common Spanish given names (low weight in matching - very generic)
COMMON_SPANISH_GIVEN_NAMES = {
    "maria", "jose", "antonio", "francisco", "juan", "manuel", "david",
    "jesus", "javier", "daniel", "carlos", "miguel", "rafael", "pedro",
    "angel", "alejandro", "fernando", "pablo", "sergio", "jorge", "luis",
    # Feminine
    "antonia", "ana", "carmen", "dolores", "isabel", "pilar", "josefa",
    "francisca", "rosa", "teresa", "mercedes", "cristina", "laura", "marta",
    "paula", "lucia", "andrea", "sara", "elena", "patricia", "raquel",
}

# Common Spanish surnames (higher weight in matching - more specific)
COMMON_SPANISH_SURNAMES = {
    "garcia", "rodriguez", "martinez", "lopez", "gonzalez", "hernandez",
    "perez", "sanchez", "ramirez", "torres", "flores", "rivera", "gomez",
    "diaz", "cruz", "morales", "reyes", "gutierrez", "ortiz", "chavez",
    "ruiz", "alvarez", "castillo", "jimenez", "moreno", "romero", "vargas",
    "fernandez", "suarez", "ramos", "vazquez", "mendez", "castro", "rojas",
    "barroso", "sevilla", "navarro", "medina", "aguilar", "cortes", "silva",
}
