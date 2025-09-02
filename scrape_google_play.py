# scrape_google_play.py — COMBINADO, balanceado por estrellas
import argparse, csv, os, time
from datetime import datetime
import pandas as pd
from google_play_scraper import reviews, Sort

def iso(dt):
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)

def append_rows(outfile, fieldnames, rows):
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    write_header = not os.path.exists(outfile) or os.path.getsize(outfile) == 0
    with open(outfile, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        if rows:
            w.writerows(rows)

def fetch_per_star(app_id, country, lang, per_star, sleep, sort):
    """Descarga hasta per_star reseñas por cada rating 1..5, usando paginación con token."""
    sort_map = {"newest": Sort.NEWEST, "most_relevant": Sort.MOST_RELEVANT}
    s = sort_map.get(sort, Sort.NEWEST)

    buckets = {1: [], 2: [], 3: [], 4: [], 5: []}
    for star in (5,4,3,2,1):
        print(f"[INFO] {app_id} {country}-{lang} → buscando {per_star} de {star}★…")
        token = None
        while len(buckets[star]) < per_star:
            batch, token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=s,
                count=200,                   # máx por página
                filter_score_with=star,
                continuation_token=token
            )
            if not batch:
                break
            need = per_star - len(buckets[star])
            buckets[star].extend(batch[:need])
            if token is None or len(buckets[star]) >= per_star:
                break
            time.sleep(sleep)
    return buckets

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--targets", required=True, help="CSV: appId,country,lang")
    p.add_argument("--out", default="out")
    p.add_argument("--per_star", type=int, default=100)
    p.add_argument("--sleep", type=float, default=0.5)
    p.add_argument("--sort", choices=["newest","most_relevant"], default="newest")
    args = p.parse_args()

    outfile = os.path.join(args.out, "google_play_all_balanced.csv")
    fieldnames = [
        "platform","appId","country","lang",
        "reviewId","userName","score","content","thumbsUpCount",
        "reviewCreatedVersion","appVersion","at","replyContent","repliedAt","reviewUrl"
    ]

    df = pd.read_csv(args.targets)
    seen_global = set()  # dedupe por (appId, reviewId)

    for _, row in df.iterrows():
        app_id = str(row["appId"]).strip()
        country = str(row["country"]).strip()
        lang = str(row["lang"]).strip()

        buckets = fetch_per_star(app_id, country, lang, args.per_star, args.sleep, args.sort)

        rows = []
        for star in (5,4,3,2,1):
            for r in buckets[star]:
                rid = r.get("reviewId")
                key = (app_id, rid)
                if rid and key in seen_global:
                    continue
                seen_global.add(key)
                rows.append({
                    "platform": "google_play",
                    "appId": app_id,
                    "country": country,
                    "lang": lang,
                    "reviewId": rid,
                    "userName": r.get("userName"),
                    "score": r.get("score"),
                    "content": r.get("content"),
                    "thumbsUpCount": r.get("thumbsUpCount"),
                    "reviewCreatedVersion": r.get("reviewCreatedVersion"),
                    "appVersion": r.get("appVersion"),
                    "at": iso(r.get("at")),
                    "replyContent": r.get("replyContent"),
                    "repliedAt": iso(r.get("repliedAt")),
                    "reviewUrl": f"https://play.google.com/store/apps/details?id={app_id}&reviewId={rid}" if rid else ""
                })

        append_rows(outfile, fieldnames, rows)
        counts = {s: len(buckets[s]) for s in (1,2,3,4,5)}
        print(f"[OK] {app_id} {country}-{lang} → +{len(rows)} filas | por estrella {counts}")

    print(f"[DONE] CSV combinado: {outfile}")

if __name__ == "__main__":
    main()