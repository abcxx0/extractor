from unidecode import unidecode
import re
import pandas as pd


# --- Definiciones globales (una sola vez) ---
EXCLUDE_CATS = {"destacadas","titulares","interes general","sin categoria"}

# — Lista limpia SOLO de países para la categoría Editorial —
PAISES_LISTA = [
    "argentina","brasil","chile","uruguay","paraguay","bolivia",
    "peru","colombia","venezuela","ecuador","mexico","canada",
    "estados unidos","eeuu","espana","francia","alemania","italia",
    "china","rusia","ucrania","india","tailandia","nueva zelanda",
    "honduras","israel"
]

# MAPEADO DIRECTO: claves en minúscula, sin tildes ni espacios irrelevantes
MAPPING_DIRECTO = {
    "politica":             "Política",
    "politicas":            "Política",
    "deporte":              "Deportes",
    "deportes":             "Deportes",
    "economia":             "Finanzas",
    "finanzas":             "Finanzas",
    "justicia":             "Justicia",
    "judicial":             "Justicia",
    "policial":             "Policial",
    "policiales":           "Policial",
    "clima":                "Clima",
    "ambiente":             "Medio Ambiente",
    "medio ambiente":       "Medio Ambiente",
    "turismo y viajes":     "Turismo y viajes",
    "turismo":              "Turismo y viajes",
    "viajes":               "Turismo y viajes",
    "precios y costo":      "Precios y costo de vida",
    "costo de vida":        "Precios y costo de vida",
    "precios cuidados":     "Precios y costo de vida",
    "tecnologia":           "Tecnología",
    "tecnologia":           "Tecnología",
    "cultura":              "Cultura",
    "entretenimiento":      "Entretenimiento",
    "internacional":        "Internacional",
    "internacionales":      "Internacional",
    "sociedad":             "Sociedad",
    "salud":                "Salud",
    "interes general":      "Interés general",
    "eventos y comunidad":  "Eventos y Comunidad",
    # extras que sacaste de categorías sucias:
    "destacadas":           None,  # quedarán ignoradas por estar en EXCLUDE_CATS
    "sin categoria":        None,
    "titulares":            None


}


# 1) Tu diccionario COMPLETO
TOPICOS = {
    "Política": [
        "congreso","camara de diputados","camara de senadores","kirchnerismo",
        "la libertad avanza","frente de todos","balotaje","boleta unica",
        "constitucion","referendum","proyecto de ley","veto",
        "intervencion federal","dnu","gabinete","jefe de gabinete","lista sabana",
        "llaryora","diputado","diputada","gobernador","gobernadora","alcalde",
        "legislativo","milei","presidente","senado","ley","gobierno","ministro",
        "macri","alberto","bullrich","ucr","peronismo","elecciones",
        "reformas politicas","decreto", "Kicillof", "Villarruel"
    ],
    "Internacional": [
        "papa francisco", "vaticano", "italia", "israel","gaza","hamas","onu","union europea","oriente medio",
        "brexit","venezuela","casa blanca","palestina","crisis migratoria",
        "brics","g20","cambio de gobierno","golpe de estado","sanciones",
        "elecciones presidenciales","cumbre climatica","eeuu","ucrania","rusia",
        "trump","otan","china","honduras","canada","alemania","ecuador",
        "nueva zelanda","relaciones diplomaticas","chile", "tailandia", "brasil", "españa"
    ],

    "Finanzas": ["credito", "linea de credito", "crediticio", "creditos", "cfi", "fmi","indec","arca","retenciones","contribuyentes","dolar","divisas", "economía circular", "déficit fiscal", "riesgo país", "deuda externa", "bonos",
    "BCRA", "reservas internacionales", "emisión monetaria",
    "tasa de interés", "superávit comercial", "balanza de pagos",
    "política monetaria", "política fiscal", "acuerdo con el FMI",
    "bonos soberanos", "canje de deuda", "banco", "linea de credito"],

    "Precios y costo de vida": [
    "precio", "canasta basica", "salari", "sueld", "acuerdo salarial", "canasta de alimento", "inflacion", "ipc", "inflacion de servicios", "inflación de bienes",
    "canasta básica", "costo de vida", "tarifas eléctricas", "tarifas de gas",
    "tarifas de agua", "transporte", "alquiler", "vivienda",
    "paritarias", "salario nominal", "salario real", "poder adquisitivo",
    "presupuesto familiar", "ajuste familiar", "consumo", "precios cuidados", "indexación", "YPF", "nafta", "descuento", "rebaja", "combustible", "índice de precios"],

    "Deportes":      [
    "Juventud Alianza", "defensa y justicia", "seleccion","mundial","copa america","champions","libertadores","sudamericana",
                  "premier league","nba","superclasico","maraton","rally","motogp","boxeo","polo",
                  "rugby","padel","surf","esports", "voley","voleibol","formula 1","f1","gran premio","clasificacion","boca","river",
                      "partido","torneo","fútbol","afa","fifa","atlético tucumán","olímpicos","deporte",
                      "gol","goles", "tenis", "basket", "handball", "cabj", "carp"],

    "Justicia":      ["corte suprema","casacion","tribunal oral","juzgado","falla","jurado","habeas corpus",
                  "amparo","recurso","sentencia firme","apelacion","indagatoria","procesamiento",
                  "sobreseimiento","condena","resolucion","acusado","defensoria", "accidente","choque","fiscalia","peritaje","hurto","robo","fiscal","juez",
                      "juicio","detención","derechos humanos","tribunales","imputaciones","investigaciones",
                      "acusacion","sentencias","reformas legales","judicial"],
    "Policial":      ["homicidio","femicidio","allanamiento","busqueda","narcomenudeo","sicarios","operativo",
                  "tiroteo","profugo","capturado","retenido","arsenal","arma blanca","arma de fuego",
                  "persecucion", "abigeato", "delitos","crimen","seguridad","investigaciones","imputaciones","detenciones",
                      "violencia","narcotráfico","corrupción","policía","crimen organizado","muerto","muerte"],

    "Clima":         ["ola de calor","ola polar","frente frio","granizo","nevadas","viento zonda",
                  "alerta amarilla","alerta naranja","alerta roja","pronostico meteorologico","humedad",
                  "fenomeno climatico", "inundación","sequía","temperatura","meteorológico","alerta","tormenta",
                      "ous meteorológico","lluvia","temporal","cambio climático","desastres naturales",
                      "inundacion","calor","temperatura","lluvias", "nieve", "SMN", "invierno", "nieve"],

    "Medio Ambiente": [
    "medio ambiente", "sustentabilidad", "ecología", "biodiversidad",
    "conservación", "contaminación", "reciclaje", "residuos",
    "cambio climático", "efecto invernadero", "huella de carbono", "sostenible", "recicl", "incendio", "deforestación", "reforestación", "forestal", "quema", "especies invasoras",
"vertido", "microplásticos", "basural", "desechos", "basura", "energía renovable", "energías limpias", "paneles solares", "eólica", "agua potable", "contaminación hídrica", "sequía", "crisis hídrica", "activismo ambiental", "educación ambiental", "regulación ambiental", "reserva natural", "fauna", "flora",
    "hábitat", "ecosistema", "protección ambiental"],

    "Eventos y Comunidad":         [ "movilizacion", "protesta", "asamblea", "acto", "encuentro",
  "feria", "festival", "carnaval", "aniversario", "festejo",
  "colecta", "donaciones", "solidaridad", "voluntariado", "merendero",
  "comedor popular", "producción ovina",
  "curso", "capacitación", "programa alimentario", "movimiento",
  "vecinal", "organizaciones sociales", "gremio", "cgt"],

    "Sociedad":         ["universidad","universidades", "docentes","maestros", "profesores", "paro docente", "violencia de genero", "perspectiva de genero", "cupo laboral", "igualdad",
  "diversidad", "derechos laborales", "inclusion", "asistencia social", "pobreza",
  "desarrollo comunitario", "programa alimentario", "educación", "escuela",
  "universidad", "docentes", "jubilados", "adultos mayores",
  "ninez", "adolescencia", "juventud", "vecinos", "comunidad", "barrio",
  "rural", "construccion", "boleto", "empleo", "paro", "paro nacional"],

    "Salud":         [
    "hantavirus", "alimento", "nutricion", "defensas", "salud mental","dengue","sarampion","chikungunya","zika","diabetes","oncologia",
                  "salud publica","consultorio","gripe aviar","emergencia sanitaria","ansiedad",
                  "obesidad","cancer","donacion de organos","trasplante","medicamentos","obra social",
                  "pami","hiv","vih","alzheimer", "adicciones","antigripal", "vacunacion","hospital","médico","epidemia","covid","enfermedad",
                      "prevención de enfermedades"],

    "Tecnología":    ["ciberseguridad","hackeo","drones","startups","fintech","big data","machine learning",
                  "deep learning","iot","semiconductores","quantum computing","nvidia","openai",
                  "metaverso","realidad mixta","biosensores","edge computing", "innovación","blockchain","realidad aumentada","app","ia","bitcoin","criptomoneda",
                      "inteligencia artificial","robot","chatgpt","iphone","samsung","celular","5g",
                      "realidad virtual","innovacion","code"],

    "Cultura":       ["museo", "exposición", "galería", "literatura", "poesía",
    "teatro", "danza", "arte", "patrimonio cultural", "patrimonio inmaterial",
    "fotografía", "coreografía", "historia del arte", "opera", "ballet",
    "música", "premio", "libro"],

    "Entretenimiento":        ["serie", "película", "streaming", "reality", "concierto",
    "festival", "musical", "stand up", "tiktok", "influencer",
    "youtuber", "oscar", "grammy", "premios", "gira",
    "ticket", "show en vivo", "farandula","GH"],

    "Turismo y viajes":         ["turismo", "turistas", "fin de semana largo", "feriado", "viaje",
    "vuelos", "aerolínea", "crucero", "hospedaje", "pasaporte",
    "visa", "aduana", "excursión", "agencia de viajes", "paquete turístico",
    "mochilero", "destino", "feriado XXL", "Air Europa", "vuelo", "aeropuerto", "flybondi", "jetsmart", "aerolineas"],

    "Interés general":["energia","medio ambiente","fin de semana largo","feriado","servicios","consumo",
                  "costumbres","tendencias","estilo de vida","hogar","mascotas","lectura","juegos",
                  "familia","ciudadania","innovacion social","responsabilidad social","seguridad vial", "turismo","turistas","gastronomía","obras","empleo","transporte público",
                      "infraestructura","turismo sostenible","abecedario"]
}

# — 1) Refinar TOPICOS["Eventos locales"] con variantes clave —
TOPICOS["Eventos locales"] = [
    "inauguracion", "inauguran", "inauguraron",
    "inscripcion", "inscripciones", "abre inscripciones",
    "capacitacion", "capacitaciones", "capacitan", "curso", "cursos",
    "taller", "talleres", "encuentro", "encuentros",
    "convocatoria", "convocatorias", "feria", "ferias",
    "festival", "festivales", "celebracion", "celebraciones",
    "celebra", "celebran", "celebrar", "festejo", "festejos",
    "homenaje", "homenajes", "rinde homenaje", "obra", "obras",
    "lanza", "lanzamiento", "lanzan", "firma", "firma un convenio",
    "se firmó un convenio"
]

# Diccionario de familias de palabras (extendible)
FAMILIAS_PALABRAS = {
    "salario": ["salarial","salariales","salarios"],
    "educación": ["educativo","educativa","educativos","educativas","educar","educación"],
}
FAMILIAS_PALABRAS = {
    "salario": ["salarial", "salariales", "salarios"],
    "educación": ["educativo", "educativa", "educativos", "educativas", "educar", "educación"],
    "credito": ["creditos", "crediticio", "crediticia", "crediticias"],
    "prestamo": ["prestamos", "creditos", "financiamiento"],
}



# Expansión de variantes (plurales y familias)
def expandir(palabras):
    s = set(palabras)
    for w in list(s):
        # plurales regulares
        if re.search(r'[aeiou]$', w):
            s |= {w + 's', w + 'es'}
        else:
            s.add(w + 'es')
        # singular de plurales
        if w.endswith('es'):
            s.add(w[:-2])
        elif w.endswith('s'):
            s.add(w[:-1])
        # familias semánticas
        if w in FAMILIAS_PALABRAS:
            s |= set(FAMILIAS_PALABRAS[w])
    return list(s)

# Normalizar antes de expandir
TOPICOS = {t: [unidecode(w).lower() for w in lst] for t, lst in TOPICOS.items()}

# Ahora sí, expande todo
TOPICOS_EXPANDIDOS = {t: expandir(lst) for t, lst in TOPICOS.items()}



# Patrón dinámico para Localidades de Córdoba
LOCALIDADES_CBA = [
    "Tajamar en Alta Gracia","Alta Gracia","Anisacate","La Paisanita","Villa General Belgrano",
    "Córdoba Capital","Mina Clavero","Villa Cura Brochero","Los Reartes","Embalse",
    "Río de los Sauces","Villa Ciudad Parque","Villa Yacanto","Marull","Achiras",
    "Villa El Chacay","Las Albahacas","Río Cuarto","Alpa Corral","Salsacate",
    "Tala Cañada","Villa de Soto","San Marcos Sierras","Cruz del Eje","San Carlos Minas",
    "Los Cocos","La Cumbre","Characato","Villa Santa Cruz del Lago","Tala Huasi",
    "San Roque","San Antonio de Arredondo","Villa Parque Siquiman","Mayu Sumaj",
    "Villa Icho Cruz","Charbonier","Cuesta Blanca","Estancia Vieja","Cabalango",
    "Villa Giardino","Villa Carlos Paz","Valle Hermoso","Tanti","Santa María de Punilla",
    "San Esteban","La Falda","Huerta Grande","Cosquín","Capilla del Monte","Bialet Massé",
    "Ischilin","Copacabana","Villa del Totoral","Villa Tulumba","Ongamira","Cerro Colorado",
    "Cañada del Río Pinto","Sinsacate","San Pedro Norte","San José de la Dormida","Quilino",
    "Deán Funes","Saldán","Agua de Oro","Ascochinga","Villa Allende","Unquillo",
    "Salsipuedes","Río Ceballos","Mendiolaza","La Calera","Jesús María","Colonia Caroya",
    "Intiyaco","El Durazno","Athos Pampa","Villa Berna","Villa Alpina","Villa Amancay",
    "Amboy","Villa Rumipal","Río Tercero","Santa Rosa de Calamuchita","Calamuchita", "Almafuerte",
    "Panaholma","San Lorenzo","Luyaba","Pampa de Achala","La Población","Las Calles",
    "Arroyo de los Patos","Villa Dolores","Villa de Las Rosas","San Javier y Yacanto",
    "Nono","Los Hornillos","Las Tapias","Las Rabonas","La Cruz","La Paz","La Para",
    "Miramar de Ansenuza","Balnearia", "La Cumbrecita", "La Serranita", "Villa Ciudad de América", "San Clemente", "Villa Los Aromos",
    "Potrero de Garay",
    "La Bolsa",
    "La Granja",
    "Villa María",
    "Falda del Carmen",
    "San Francisco del Chañar", "Calmayo",
    "Villa Ascasubi"
]


## 3. Función de expansión
def expandir(palabras):
    s = set()
    for w in palabras:
        s.add(w)
        if re.search(r'[aeiou]$', w):
            s.add(w + 's')
            s.add(w + 'es')
        else:
            s.add(w + 'es')
        if w.endswith('es'):
            s.add(w[:-2])
        elif w.endswith('s'):
            s.add(w[:-1])
        if w in FAMILIAS_PALABRAS:
            s |= set(FAMILIAS_PALABRAS[w])
    return list(s)


# Patrón dinámico para Localidades de Córdoba
LOCALIDADES_CBA = [
    "Tajamar en Alta Gracia","Alta Gracia","Anisacate","La Paisanita","Villa General Belgrano",
    "Córdoba Capital","Mina Clavero","Villa Cura Brochero","Los Reartes","Embalse",
    "Río de los Sauces","Villa Ciudad Parque","Villa Yacanto","Marull","Achiras",
    "Villa El Chacay","Las Albahacas","Río Cuarto","Alpa Corral","Salsacate",
    "Tala Cañada","Villa de Soto","San Marcos Sierras","Cruz del Eje","San Carlos Minas",
    "Los Cocos","La Cumbre","Characato","Villa Santa Cruz del Lago","Tala Huasi",
    "San Roque","San Antonio de Arredondo","Villa Parque Siquiman","Mayu Sumaj",
    "Villa Icho Cruz","Charbonier","Cuesta Blanca","Estancia Vieja","Cabalango",
    "Villa Giardino","Villa Carlos Paz","Valle Hermoso","Tanti","Santa María de Punilla",
    "San Esteban","La Falda","Huerta Grande","Cosquín","Capilla del Monte","Bialet Massé",
    "Ischilin","Copacabana","Villa del Totoral","Villa Tulumba","Ongamira","Cerro Colorado",
    "Cañada del Río Pinto","Sinsacate","San Pedro Norte","San José de la Dormida","Quilino",
    "Deán Funes","Saldán","Agua de Oro","Ascochinga","Villa Allende","Unquillo",
    "Salsipuedes","Río Ceballos","Mendiolaza","La Calera","Jesús María","Colonia Caroya",
    "Intiyaco","El Durazno","Athos Pampa","Villa Berna","Villa Alpina","Villa Amancay",
    "Amboy","Villa Rumipal","Río Tercero","Santa Rosa de Calamuchita","Calamuchita", "Almafuerte",
    "Panaholma","San Lorenzo","Luyaba","Pampa de Achala","La Población","Las Calles",
    "Arroyo de los Patos","Villa Dolores","Villa de Las Rosas","San Javier y Yacanto",
    "Nono","Los Hornillos","Las Tapias","Las Rabonas","La Cruz","La Paz","La Para",
    "Miramar de Ansenuza","Balnearia", "La Cumbrecita", "La Serranita", "Villa Ciudad de América", "San Clemente", "Villa Los Aromos",
    "Potrero de Garay",
    "La Bolsa",
    "La Granja",
    "Villa María",
    "Falda del Carmen",
    "San Francisco del Chañar", "Calmayo",
    "Villa Ascasubi"
]
# Patrón dinámico para Localidades de Córdoba
LOCAL_PATS = []
for loc in LOCALIDADES_CBA:
    name = unidecode(loc).lower()
    # 1) Nombre completo: reemplazamos espacios por \s+ **antes**
    name_pattern = name.replace(' ', r'\\s+')
    LOCAL_PATS.append(fr"\b{name_pattern}\b")
    # 2) Última palabra del topónimo
    parts = name.split()
    if len(parts) > 1:
        LOCAL_PATS.append(fr"\b{parts[-1]}\b")


def clasificar_noticia(titulo, cats_str):
    tl   = unidecode(titulo).lower()
    cats = unidecode(cats_str or '').lower()

    # 1) Mapeo directo por substring (más robusto para plurales y espacios)
    for raw in cats.split(','):
        key = raw.strip()
        if not key or key in EXCLUDE_CATS:
            continue
        for pat, top in MAPPING_DIRECTO.items():
            if pat in key and top is not None:
                return top
# 1.5) Si la categoría menciona un país, usar Internacional
    for pais in PAISES_LISTA:
        if pais in cats:
            return 'Internacional'

    # 2) Internacional (sólo keywords de países)
    for w in TOPICOS_EXPANDIDOS.get('Internacional', []):
        if re.search(rf"\b{re.escape(w)}\b", tl):
            return 'Internacional'

    # 3) Policial (root matching)
    for w in TOPICOS_EXPANDIDOS.get('Policial', []):
        if re.search(rf"\b{re.escape(w)}\w*\b", tl):
            return 'Policial'

    # 4) Política
    for w in TOPICOS_EXPANDIDOS.get('Política', []):
        if re.search(rf"\b{re.escape(w)}\w*\b", tl):
            return 'Política'

     # 5) Precios y costo de vida (muy específico)
    for w in TOPICOS_EXPANDIDOS.get('Precios y costo de vida', []):
        if re.search(rf'\b{re.escape(w)}\w*\b', tl):
            return 'Precios y costo de vida'

    # 6) Finanzas (macro)
    fin_keys = (TOPICOS_EXPANDIDOS.get('Finanzas', []) +
                TOPICOS_EXPANDIDOS.get('Precios y costo de vida', []))
    for w in fin_keys:
        if re.search(rf'\b{re.escape(w)}\w*\b', tl):
            return 'Finanzas'

    # 7) Salud
    for w in TOPICOS_EXPANDIDOS.get('Salud', []):
        if re.search(rf'\b{re.escape(w)}\w*\b', tl):
            return 'Salud'

    # 8) Eventos locales: localidad + keyword de evento (match infijo)
    locals_found = [
        pat for pat in LOCAL_PATS
        if re.search(pat, tl, flags=re.IGNORECASE)
    ]
    if len(locals_found) >= 2:
        return 'Eventos locales'

    for evt in TOPICOS_EXPANDIDOS['Eventos locales']:
        # permitimos que la raíz aparezca en cualquier parte de la palabra
        pattern = rf'\b\w*{re.escape(evt)}\w*\b'
        if re.search(pattern, tl, flags=re.IGNORECASE):
            return 'Eventos locales'


    # 9) Otros tópicos genéricos
    skip = {'Internacional','Policial','Política','Finanzas','Precios y costo de vida','Eventos locales'}
    for topico, palabras in TOPICOS_EXPANDIDOS.items():
        if topico in skip:
            continue
        for w in palabras:
            if re.search(rf"\b{re.escape(w)}\b", tl):
                return topico

    # 10) Fallback
    return 'Otros'

# --- Aplicar clasificación y guardar resultados ---
df = pd.read_csv('datos_actualizados.csv', sep=';', encoding='utf-8')

df['Topico_Final'] = df.apply(
    lambda x: clasificar_noticia(x['Título'], x.get('Categorías', '')), axis=1
)

# Guarda resultado en datos_clasificados.csv
df.to_csv('datos_clasificados.csv', index=False)

print("✅ Clasificación terminada. CSV generado en datos_clasificados.csv.")

