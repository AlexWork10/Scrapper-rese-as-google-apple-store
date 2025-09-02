import argparse, csv, os, time
from datetime import datetime
from collections import defaultdict
import pandas as pd
import requests

def iso(s):
    if not s:
        return ""
    # El RSS ya viene ISO-like; devolvemos tal cual para no romper TZ
    return str(s)

def append_rows(outfile, fieldnames, rows):
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    write_header = not os.path.exists(outfile) or os.path.getsize(outfile) == 0
    with open(outfile, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        if rows:
            w.writerows(rows)

def guess_lang(country):
    m = {
        "us": "en", "gb": "en", "au": "en", "ca": "en",
        "es": "es", "mx": "es", "ar": "es", "co": "es", "cl": "es", "pe": "es",
        "fr": "fr", "de": "de", "it": "it", "br": "pt", "pt": "pt"
    }
    return m.get(country.lower(), "en")

def fetch_balanced_rss(app_id, country, app_name, per_star, max_pages, sleep, lang=None):
    """
    Usa el RSS JSON de Apple:
    https://itunes.apple.com/rss/customerreviews/page={n}/id={app_id}/sortby=mostrecent/json?l={lang}&cc={country}
    Devuelve (app_name_detected, buckets_por_estrella)
    """
    if not lang:
        lang = guess_lang(country)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    buckets = defaultdict(list)  # {1:[],...,5:[]}
    seen = set()
    detected_name = app_name

    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        params = {"l": lang, "cc": country}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code != 200:
                print(f"[WARN] {app_id} {country} p{page} → HTTP {resp.status_code}")
                if resp.status_code in (403, 429):
                    time.sleep(sleep * 2)
                continue
            data = resp.json()
        except Exception as e:
            print(f"[WARN] {app_id} {country} p{page} → error leyendo JSON: {e}")
            time.sleep(sleep)
            continue

        feed = data.get("feed", {})
        entries = feed.get("entry", [])
        if not entries:
            # Nada más que leer en este storefront
            break

        # La primera entry suele ser metadata de la app
        if not detected_name:
            try:
                meta = entries[0]
                detected_name = meta.get("im:name", {}).get("label", app_name)
            except Exception:
                pass

        # El resto son reseñas
        reviews_entries = entries[1:] if len(entries) > 1 else []
        if not reviews_entries and page == 1:
            # Este storefront puede no tener reseñas públicas
            print(f"[INFO] {app_id} {country} → sin reseñas visibles en RSS.")
            break

        for e in reviews_entries:
            try:
                rating = int(e.get("im:rating", {}).get("label"))
            except Exception:
                continue
            author = (e.get("author", {}) or {}).get("name", {}).get("label")
            title = (e.get("title", {}) or {}).get("label")
            content = (e.get("content", {}) or {}).get("label")
            date = (e.get("updated", {}) or {}).get("label")

            key = (author, title, date, rating, content)
            if key in seen:
                continue
            seen.add(key)

            if 1 <= rating <= 5 and len(buckets[rating]) < per_star:
                buckets[rating].append({
                    "userName": author,
                    "rating": rating,
                    "title": title,
                    "review": content,
                    "date": iso(date),
                    "isEdited": ""  # el RSS no incluye flag de edición
                })

        counts = {s: len(buckets[s]) for s in (1,2,3,4,5)}
        print(f"[INFO] {app_id} {country} p{page} lang={lang} → {counts}")

        if all(len(buckets[s]) >= per_star for s in (1,2,3,4,5)):
            break

        time.sleep(sleep)

    return detected_name, buckets

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True, help="CSV: app_id,country,app_name[,lang(opcional)]")
    ap.add_argument("--out", default="out")
    ap.add_argument("--per_star", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max_pages", type=int, default=20, help="Páginas RSS a recorrer por app/país (50 reviews/página aprox.)")
    args = ap.parse_args()

    outfile = os.path.join(args.out, "app_store_all_balanced.csv")
    fieldnames = ["platform","app_id","country","app_name","userName","rating","title","review","date","isEdited"]

    df = pd.read_csv(args.targets)
    seen_global = set()

    for _, row in df.iterrows():
        app_id = str(row["app_id"]).strip()
        country = str(row["country"]).strip().lower()
        app_name = (str(row["app_name"]).strip() if "app_name" in row and pd.notna(row["app_name"]) else None)
        lang = (str(row["lang"]).strip().lower() if "lang" in df.columns and pd.notna(row.get("lang")) else None)

        print(f"[INFO] RSS → id={app_id} country={country} name='{app_name or ''}'")
        detected_name, buckets = fetch_balanced_rss(
            app_id=app_id,
            country=country,
            app_name=app_name,
            per_star=args.per_star,
            max_pages=args.max_pages,
            sleep=args.sleep,
            lang=lang
        )

        rows = []
        for star in (5,4,3,2,1):
            for r in buckets[star]:
                key = (app_id, country, r["userName"], r["title"], r["date"], r["rating"], r["review"])
                if key in seen_global:
                    continue
                seen_global.add(key)
                rows.append({
                    "platform": "app_store",
                    "app_id": app_id,
                    "country": country,
                    "app_name": detected_name or app_name or "",
                    "userName": r["userName"],
                    "rating": r["rating"],
                    "title": r["title"],
                    "review": r["review"],
                    "date": r["date"],
                    "isEdited": r["isEdited"],
                })

        append_rows(outfile, fieldnames, rows)
        print(f"[OK] {app_id} {country} → añadidas {len(rows)} filas al combinado")

    print(f"[DONE] CSV combinado: {outfile}")

if __name__ == "__main__":
    main()
