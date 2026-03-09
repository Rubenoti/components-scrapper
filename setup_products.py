"""
Script de setup inicial — añade los productos del build a la DB.
Edita las URLs y precios objetivo según lo que vayas encontrando.

Ejecutar una vez:
    python setup_products.py
"""
from db.database import init_db, upsert_product
from models.product import Product


PRODUCTS = [
    # ─── GPU (objetivo segunda mano Wallapop) ────────────────────────────────
    Product(
        id=None,
        name="RTX 3090 24GB",
        url="",  # Wallapop usa keyword, no URL directa
        source="wallapop",
        target_price=550.0,
        category="gpu",
        notes="Sin historial minero. Verificar con FurMark antes de comprar.",
    ),

    # ─── CPU ─────────────────────────────────────────────────────────────────
    Product(
        id=None,
        name="AMD Ryzen 5 7600",
        url="https://www.pccomponentes.com/amd-ryzen-5-7600-38ghz",
        source="pccomponentes",
        target_price=155.0,
        category="cpu",
        notes="Incluye disipador Wraith Stealth.",
    ),

    # ─── Placa base ──────────────────────────────────────────────────────────
    Product(
        id=None,
        name="ASUS TUF Gaming X670E-Plus WiFi",
        url="https://www.pccomponentes.com/asus-tuf-gaming-x670e-plus-wifi",
        source="pccomponentes",
        target_price=200.0,
        category="mobo",
        notes="2x PCIe x16 real. Soporta hasta 128GB DDR5.",
    ),

    # ─── RAM ─────────────────────────────────────────────────────────────────
    Product(
        id=None,
        name="Kingston Fury Beast 32GB DDR5-6000 CL30",
        url="https://www.pccomponentes.com/kingston-fury-beast-32gb-2x16gb-ddr5-6000mhz-cl30",
        source="pccomponentes",
        target_price=90.0,
        category="ram",
        notes="Perfil EXPO para AM5. Alternativamente G.Skill Flare X5.",
    ),

    # ─── Fuente de alimentación ───────────────────────────────────────────────
    Product(
        id=None,
        name="Seasonic Focus GX-1000W 80+ Gold",
        url="https://www.pccomponentes.com/seasonic-focus-gx-1000w-80-plus-gold",
        source="pccomponentes",
        target_price=150.0,
        category="psu",
        notes="1000W para soportar 2x 3090 en el futuro. ATX 3.0.",
    ),

    # ─── SSD ─────────────────────────────────────────────────────────────────
    Product(
        id=None,
        name="WD Black SN850X 1TB NVMe Gen4",
        url="https://www.pccomponentes.com/wd-black-sn850x-1tb-nvme-m2",
        source="pccomponentes",
        target_price=70.0,
        category="ssd",
        notes="Gen4. Alternativa: Samsung 990 Pro.",
    ),

    # ─── Caja ─────────────────────────────────────────────────────────────────
    Product(
        id=None,
        name="Fractal Design Pop Air ATX",
        url="https://www.pccomponentes.com/fractal-design-pop-air-negro",
        source="pccomponentes",
        target_price=65.0,
        category="case",
        notes="Buen airflow para la 3090. Alternativa: Lian Li Lancool 216.",
    ),
]


if __name__ == "__main__":
    init_db()
    for p in PRODUCTS:
        pid = upsert_product(p)
        print(f"✅ Añadido: {p.name} (id={pid}) | objetivo: {p.target_price}€ | fuente: {p.source}")

    print(f"\n{len(PRODUCTS)} productos listos. Ejecuta 'python tracker.py' para el primer ciclo.")