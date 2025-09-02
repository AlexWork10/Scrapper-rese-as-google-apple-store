# 0) (opcional) limpiar combinados previos para no duplicar
rm -f out/google_play_all_balanced.csv out/app_store_all_balanced.csv out/reviews_all.csv

# 1) activar el entorno
source .venv/bin/activate

python scrape_google_play.py \
  --targets google_play_targets.csv \
  --out out \
  --per_star 200 \
  --sleep 1.0 \
  --sort newest

# App Store (mantén el script RSS que ya te funcionó antes)
python scrape_app_store.py \
  --targets app_store_targets.csv \
  --out out \
  --per_star 200 \
  --sleep 1 \
  --max_pages 20
