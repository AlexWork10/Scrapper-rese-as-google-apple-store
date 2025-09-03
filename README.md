# GetReviewsGoogle&AppleStore

Scripts para obtener reseñas de aplicaciones de Google Play Store y Apple App Store.

## Instalación

### 1. Crear entorno virtual

```bash
# Crear el entorno virtual
python3 -m venv .venv

# Activar el entorno virtual
# En macOS/Linux:
source .venv/bin/activate

# En Windows:
# .venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
# Con el entorno virtual activado, instalar requirements
pip install -r requirements.txt
```

## Uso

### 1. Limpiar archivos previos (opcional)
```bash
rm -f out/google_play_all_balanced.csv out/app_store_all_balanced.csv out/reviews_all.csv
```

### 2. Obtener reseñas de Google Play Store
```bash
python scrape_google_play.py \
  --targets google_play_targets.csv \
  --out out \
  --per_star 200 \
  --sleep 1.0 \
  --sort newest
```

### 3. Obtener reseñas de Apple App Store
```bash
python scrape_app_store.py \
  --targets app_store_targets.csv \
  --out out \
  --per_star 200 \
  --sleep 1 \
  --max_pages 20
```

## Estructura de archivos

- `scrape_google_play.py` - Script para Google Play Store
- `scrape_app_store.py` - Script para Apple App Store
- `google_play_targets.csv` - Lista de aplicaciones de Google Play
- `app_store_targets.csv` - Lista de aplicaciones de App Store
- `out/` - Carpeta de salida con los resultados
- `requirements.txt` - Dependencias de Python

## Notas

- Asegúrate de tener el entorno virtual activado antes de ejecutar los scripts
- Los archivos de salida se guardan en la carpeta `out/`
- Ajusta los parámetros según tus necesidades (número de reseñas por estrella, tiempo de espera, etc.)
