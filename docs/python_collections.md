# Python `collections` — Estructuras que optimizan el código

Cuando aprendés Python, trabajás con `list`, `dict` y `tuple`.
Funcionan para casi todo, pero tienen costos ocultos en casos específicos.
El módulo `collections` resuelve esos casos con herramientas diseñadas para cada problema.

La diferencia entre saber y no saber estas estructuras es la diferencia entre
tomar el camino corto o el camino largo.

---

## `deque` — Cola de doble extremo con tamaño máximo

**El problema que resuelve:** mantener las últimas N cosas sin gestionar el tamaño manualmente.

```python
from collections import deque

# Sin deque — gestión manual
historial = []
historial.append(nueva_entrada)
if len(historial) > 3:
    historial.pop(0)  # lento: mueve todos los elementos

# Con deque — automático y eficiente
historial = deque(maxlen=3)
historial.append(nueva_entrada)  # el más viejo se borra solo
```

**Por qué es más rápido:** `list.pop(0)` es O(n) — mueve todos los elementos.
`deque.popleft()` es O(1) — operación en tiempo constante.

**Dónde lo usamos:** `rag_chain.py` — historial conversacional de las últimas 3 interacciones.
Si no supiéramos `deque`, el historial sería una lista con pop manual.

**Otros métodos útiles:**
```python
d = deque([1, 2, 3], maxlen=3)
d.appendleft(0)   # agrega al inicio → [0, 1, 2] (el 3 se fue)
d.popleft()       # saca del inicio → [1, 2]
d.rotate(1)       # rota → [2, 1]  (útil para buffers circulares)
```

**Cuándo usar deque vs list:**
- `list` → cuando necesitás acceso por índice (`d[5]`, `d[-1]`)
- `deque` → cuando solo trabajás con los extremos y querés tamaño máximo

---

## `Counter` — Contador de ocurrencias

**El problema que resuelve:** contar cuántas veces aparece cada elemento sin escribir el loop manualmente.

```python
from collections import Counter

# Sin Counter — manual
texto = "aaaaabbc"
conteo = {}
for c in texto:
    conteo[c] = conteo.get(c, 0) + 1
# {'a': 5, 'b': 2, 'c': 1}

# Con Counter — una línea
conteo = Counter(texto)
# Counter({'a': 5, 'b': 2, 'c': 1})
```

**Métodos clave:**
```python
c = Counter("mississippi")

c.most_common(2)    # [('s', 4), ('i', 4)] — los N más comunes
c.most_common(1)[0] # ('s', 4) — el más común con su count

# Aritmética entre counters
c1 = Counter("aab")
c2 = Counter("abc")
c1 + c2  # Counter({'a': 3, 'b': 2, 'c': 1})
c1 - c2  # Counter({'a': 1}) — solo positivos
```

**Dónde lo usamos:** `main.py` — input firewall.
Para detectar si un carácter ocupa más del 40% del input (ej: "aaaaaaaaaa"):

```python
char_counts = Counter(texto.replace(" ", ""))
char, count  = char_counts.most_common(1)[0]
if count / total > 0.40:
    return False, "repetición de caracter"
```

Sin `Counter`, necesitarías un dict manual + ordenamiento.

---

## `defaultdict` — Diccionario con valor por defecto

**El problema que resuelve:** eliminar el `KeyError` cuando accedés a una key que no existe.

```python
from collections import defaultdict

# Sin defaultdict — hay que verificar si la key existe
grupos = {}
for palabra in ["python", "java", "pytorch", "javascript"]:
    primera = palabra[0]
    if primera not in grupos:
        grupos[primera] = []
    grupos[primera].append(palabra)

# Con defaultdict — la lista se crea sola
grupos = defaultdict(list)
for palabra in ["python", "java", "pytorch", "javascript"]:
    grupos[palabra[0]].append(palabra)
# {'p': ['python', 'pytorch'], 'j': ['java', 'javascript']}
```

**El argumento es un callable** — le decís qué tipo crear cuando falta la key:
```python
defaultdict(list)   # crea [] para keys nuevas
defaultdict(int)    # crea 0  para keys nuevas
defaultdict(set)    # crea set() para keys nuevas
defaultdict(dict)   # crea {} para keys nuevas
```

**Caso de uso típico:** agrupar elementos, acumular valores, construir grafos.

**Nota:** si accedés a una key que no existe, la crea. A veces eso no es lo que querés —
en esos casos usá `dict.get(key, default)` que no crea la key.

---

## `namedtuple` — Tupla con nombres de campo

**El problema que resuelve:** tuplas con significado, sin overhead de una clase completa.

```python
from collections import namedtuple

# Sin namedtuple — ¿qué significa [1]?
punto = (10, 20)
print(punto[0])  # x? longitud? id?

# Con namedtuple — autoexplicado
Punto = namedtuple("Punto", ["x", "y"])
p = Punto(10, 20)
print(p.x)    # 10 — claro
print(p.y)    # 20 — claro
print(p[0])   # 10 — sigue funcionando como tupla
```

**Inmutable como tupla, legible como objeto:**
```python
Chunk = namedtuple("Chunk", ["texto", "fuente", "score"])
c = Chunk(texto="trabajé con spaCy", fuente="perfil.md", score=0.87)

c.texto   # "trabajé con spaCy"
c.fuente  # "perfil.md"
c.score   # 0.87

# No se puede modificar — es inmutable
c.texto = "otro"  # AttributeError
```

**Cuándo usar namedtuple vs dataclass:**
- `namedtuple` → datos inmutables, liviano, compatible con tupla
- `dataclass` → necesitás mutabilidad, métodos, o valores default complejos

**En el contexto del proyecto:** podría usarse para tipar los chunks de ChromaDB
o las respuestas del router, haciendo el código más legible sin agregar clases completas.

---

## `OrderedDict` — Diccionario con orden garantizado

**Nota histórica:** desde Python 3.7 los `dict` normales mantienen orden de inserción.
`OrderedDict` sigue siendo útil por un método específico:

```python
from collections import OrderedDict

od = OrderedDict()
od["a"] = 1
od["b"] = 2
od["c"] = 3

od.move_to_end("a")        # mueve "a" al final
od.move_to_end("c", last=False)  # mueve "c" al inicio
```

**Caso de uso real:** implementar una caché LRU (Least Recently Used) —
cuando la caché está llena, eliminar el elemento menos usado recientemente.
El historial del bot podría implementarse así si se quisiera priorizar por uso
en lugar de por orden cronológico.

---

## Resumen — cuándo usar cada uno

| Estructura    | Úsala cuando...                                          |
|---------------|----------------------------------------------------------|
| `deque`       | Necesitás las últimas N cosas / cola / stack eficiente   |
| `Counter`     | Contar ocurrencias de elementos                          |
| `defaultdict` | Agrupar o acumular sin verificar si la key existe        |
| `namedtuple`  | Datos estructurados inmutables sin clase completa        |
| `OrderedDict` | Necesitás `move_to_end` / caché LRU                      |

La regla general: si estás escribiendo un `if key not in dict`, un `pop(0)` en una lista,
o un loop para contar — probablemente hay una estructura de `collections` que lo hace mejor.
