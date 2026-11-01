import difflib
import re

ALIASES = {
    'toshkent': {'toshkent', 'tashkent', 'tosh', 'tash'},
    'samarqand': {'samarqand', 'samarkand', 'samarkant'},
    'buxoro': {'buxoro', 'buxara', 'bukhara', 'buhoro'},
    'andijon': {'andijon', 'andijan'},
    'namangan': {'namangan'},
    'fargona': {'fargona', "farg'ona", "farg‘ona", 'fergana', 'fergona'},
    'qashqadaryo': {'qashqadaryo', 'kashkadarya', 'qarshi', 'karshi', 'koson', 'kason', 'kasan', 'shahrisabz', 'shaxrisabz'},
    'surxondaryo': {'surxondaryo', 'surxandarya', 'termiz', 'termez'},
    'xorazm': {'xorazm', 'khorezm', 'horazm', 'urganch', 'urgench', 'xiva'},
    'navoiy': {'navoiy', 'navoi'},
    'jizzax': {'jizzax', 'djizak', 'jizak'},
    'sirdaryo': {'sirdaryo', 'sirdarya', 'guliston', 'gulistan'},
    'qoraqalpogiston': {'qoraqalpogiston', 'karakalpakstan', 'nukus', 'nókis', 'nokis'},
    'koson': {'koson', 'kason', 'kasan', 'kassan'},
    'nukus': {'nukus', 'nókis', 'nokis'},
    'qarshi': {'qarshi', 'karshi'},
}

STOPWORDS = {
    'tumani', 'tuman', 'viloyati', 'viloyat', 'shahri', 'shahar', 
    'vil', 'sh', 't', 'rayon', 'oblast', 'gorod', 'oʻzbekiston', 
    'ozbekiston', 'uzbekistan', 'respublikasi', 'resp'
}

def clean_and_tokenize(text: str):
    if not text:
        return []
    cleaned = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF\u02BB\u02BC\'`\u00F3\u00D3]', ' ', text.lower())
    words = cleaned.split()
    tokens = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return tokens

def phonetic_key(word: str) -> str:
    w = word.lower()
    w = w.replace('ó', 'o').replace('oʻ', 'o').replace("o'", 'o').replace('o`', 'o')
    w = w.replace('gʻ', 'g').replace("g'", 'g').replace('g`', 'g')
    w = w.replace('kh', 'x').replace('h', 'x')
    w = w.replace('q', 'k')
    w = w.replace('c', 's')
    w = w.replace('dj', 'j')
    w = re.sub(r'[aou]', '*', w)
    w = re.sub(r'[ei]', '#', w)
    w = re.sub(r'(.)\1+', r'\1', w)
    return w

def is_word_match(w1: str, w2: str) -> bool:
    w1_l = w1.lower()
    w2_l = w2.lower()
    if w1_l == w2_l:
        return True
    if w1_l in w2_l or w2_l in w1_l:
        return True
        
    for key, group in ALIASES.items():
        if (w1_l in group or key == w1_l) and (w2_l in group or key == w2_l):
            return True

    if phonetic_key(w1) == phonetic_key(w2):
        return True

    if len(w1) >= 4 and len(w2) >= 4:
        sim = difflib.SequenceMatcher(None, w1_l, w2_l).ratio()
        if sim >= 0.70:
            return True
            
    return False

def location_matches(query: str, target: str) -> bool:
    q_tokens = clean_and_tokenize(query)
    t_tokens = clean_and_tokenize(target)
    
    if not q_tokens:
        return True
    if not t_tokens:
        return False
        
    for qw in q_tokens:
        for tw in t_tokens:
            if is_word_match(qw, tw):
                return True
    return False

test_db = [
    {"origin": "Toshkent, Oʻzbekiston", "dest": "Nókis, Oʻzbekiston"},
    {"origin": "Qashqadaryo viloyati, koson tumani", "dest": "Namangan viloyati,"},
    {"origin": "Farg'ona viloyati,", "dest": "Navoiy viloyati,"},
    {"origin": "Samarkand", "dest": "Buxoro viloyati,"},
]

queries = [
    ('koson tumani', 'namangan'),
    ('kason', 'namangan'),        # typo: kason -> koson
    ('koson', 'namangan shahar'),
    ('samarqand', 'buxoro'),       # samarqand vs Samarkand
    ('samarkand', 'buxara'),       # buxara vs Buxoro
    ('tashkent', 'nukus'),         # tashkent vs Toshkent, nukus vs Nókis
    ('qashqadaryo', 'namangan'),
]

for q_from, q_to in queries:
    matched = []
    for item in test_db:
        if location_matches(q_from, item['origin']) and location_matches(q_to, item['dest']):
            matched.append(f"{item['origin']} -> {item['dest']}")
    print(f"Q: ({q_from} -> {q_to}) => Matches: {len(matched)}: {matched}")
