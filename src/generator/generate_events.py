"""Générateur d'événements e-commerce (visites, paniers, achats) au format JSON Lines."""
import argparse
import json
import random
import uuid
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path

from faker import Faker

fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)

# Catégories et fourchette de prix en MAD
CATEGORIES = {
    "Électronique": (500, 15000),
    "Mode": (100, 1500),
    "Maison": (80, 4000),
    "Beauté": (50, 800),
    "Sport": (100, 3000),
}
CITIES = ["Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", "Agadir", "Meknès", "Oujda"]
CITY_WEIGHTS = [35, 15, 12, 10, 10, 8, 5, 5]
DEVICES = ["mobile", "desktop", "tablet"]
DEVICE_WEIGHTS = [60, 32, 8]
# Plus de trafic le soir qu'en pleine nuit
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 3, 5, 6, 6, 6, 7, 8, 7, 6, 6, 7, 8, 10, 12, 12, 10, 6, 3]


def make_products(n=50):
    products = []
    for i in range(1, n + 1):
        category = random.choice(list(CATEGORIES))
        low, high = CATEGORIES[category]
        products.append({
            "product_id": f"P{i:04d}",
            "name": f"{category} - {fake.word().capitalize()}",
            "category": category,
            "price": round(random.uniform(low, high), 2),
        })
    return products


def make_customers(n=1000):
    return [
        {
            "customer_id": f"C{i:05d}",
            "name": fake.name(),
            "email": fake.email(),
            "city": random.choices(CITIES, weights=CITY_WEIGHTS)[0],
            "signup_date": fake.date_between("-2y", "-30d").isoformat(),
        }
        for i in range(1, n + 1)
    ]


def random_start(end, days):
    day = end.date() - timedelta(days=random.randint(1, days))
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    return datetime.combine(day, time(hour, random.randint(0, 59), random.randint(0, 59)))


def make_event(event_type, t, session_id, customer, product, device, **extra):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_time": t.isoformat(timespec="seconds"),
        "session_id": session_id,
        "customer_id": customer["customer_id"],
        "product_id": product["product_id"],
        "category": product["category"],
        "price": product["price"],
        "device": device,
        **extra,
    }


def make_session(customer, products, start):
    """Une visite : produits vus -> certains ajoutés au panier -> parfois un achat."""
    session_id = str(uuid.uuid4())
    device = random.choices(DEVICES, weights=DEVICE_WEIGHTS)[0]
    t = start
    events, cart = [], []

    for product in random.sample(products, k=random.randint(1, 6)):
        events.append(make_event("page_view", t, session_id, customer, product, device))
        t += timedelta(seconds=random.randint(10, 180))
        if random.random() < 0.30:
            qty = random.choices([1, 2, 3], weights=[80, 15, 5])[0]
            events.append(make_event("add_to_cart", t, session_id, customer, product, device, quantity=qty))
            cart.append((product, qty))
            t += timedelta(seconds=random.randint(5, 60))

    if cart and random.random() < 0.40:
        order_id = f"O-{uuid.uuid4().hex[:10].upper()}"
        t += timedelta(seconds=random.randint(30, 300))
        for product, qty in cart:
            events.append(make_event("purchase", t, session_id, customer, product, device,
                                     quantity=qty, order_id=order_id))
    return events


def add_noise(events, rate=0.02):
    """Ajoute des erreurs volontaires que la couche silver devra nettoyer."""
    noisy = []
    for e in events:
        r = random.random()
        if r < rate:                      # doublon exact
            noisy.extend([e, dict(e)])
        elif r < rate * 1.5:              # client manquant
            noisy.append({**e, "customer_id": None})
        elif r < rate * 1.75:             # prix négatif
            noisy.append({**e, "price": -abs(e["price"])})
        else:
            noisy.append(e)
    return noisy


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=20000)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", default="data/landing")
    args = parser.parse_args()

    out = Path(args.output)
    (out / "events").mkdir(parents=True, exist_ok=True)

    products = make_products()
    customers = make_customers()
    write_jsonl(out / "products.json", products)
    write_jsonl(out / "customers.json", customers)

    end = datetime.now()
    by_day = defaultdict(list)
    for _ in range(args.sessions):
        start = random_start(end, args.days)
        by_day[start.date()].extend(make_session(random.choice(customers), products, start))

    total = 0
    for day, events in sorted(by_day.items()):
        events = add_noise(events)
        write_jsonl(out / "events" / f"events_{day}.json", events)
        total += len(events)

    print(f"{len(products)} produits, {len(customers)} clients, {total} événements sur {len(by_day)} jours")


if __name__ == "__main__":
    main()