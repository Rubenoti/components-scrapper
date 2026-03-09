"""
Script de setup inicial — añade los productos del build a la DB.
URLs verificadas en PcComponentes en marzo 2026.

Ejecutar una vez:
    python setup_products.py
"""
from db.database import init_db, upsert_product
from models.product import Product


PRODUCTS = [
    # ─── GPU (objetivo segunda mano Wallapop) ────────────────────────────────
    # Wallapop no usa URL directa, busca por keyword
    Product(
        id=None,
        name="RTX 3090 24GB",
        url="",
        source="wallapop",
        target_price=550.0,
        category="gpu",
        notes="Sin historial minero. Verificar con FurMark antes de comprar. Buscar también '3090 Ti'.",
    ),

    # ─── CPU ─────────────────────────────────────────────────────────────────
    # URL verificada ✅
    Product(
        id=None,
        name="AMD Ryzen 5 7600",
        url="https://www.pccomponentes.com/amd-ryzen-5-7600-38-51-ghz-box",
        source="pccomponentes",
        target_price=155.0,
        category="cpu",
        notes="Incluye disipador Wraith Stealth. 65W nominal.",
    ),

    # ─── Placa base ──────────────────────────────────────────────────────────
    # URL verificada ✅ (también hay versión sin WiFi más barata)
    Product(
        id=None,
        name="ASUS TUF Gaming X670E-Plus WiFi",
        url="https://www.pccomponentes.com/asus-tuf-gaming-x670e-plus-wifi",
        source="pccomponentes",
        target_price=200.0,
        category="mobo",
        notes="2x PCIe 5.0 x16. 4x M.2. WiFi 6E. Soporta hasta 128GB DDR5.",
    ),

    # ─── Alternativa placa base (sin WiFi, algo más barata) ──────────────────
    Product(
        id=None,
        name="ASUS TUF Gaming X670E-Plus (sin WiFi)",
        url="https://www.pccomponentes.com/asus-tuf-gaming-x670e-plus",
        source="pccomponentes",
        target_price=180.0,
        category="mobo",
        notes="Alternativa sin WiFi. Mismas especificaciones PCIe.",
    ),

    # ─── RAM — versión CL30 (mejor latencia) ─────────────────────────────────
    # URL verificada ✅
    Product(
        id=None,
        name="Kingston Fury Beast DDR5 6000MHz 32GB CL30",
        url="https://www.pccomponentes.com/kingston-fury-beast-ddr5-6000mhz-32gb-2x16gb-cl30",
        source="pccomponentes",
        target_price=90.0,
        category="ram",
        notes="CL30 es mejor que CL36. Perfil XMP 3.0 (compatible EXPO en AM5 via BIOS).",
    ),

    # ─── RAM — alternativa con EXPO nativo ───────────────────────────────────
    # URL verificada ✅
    Product(
        id=None,
        name="Kingston 32GB DDR5 6000MT/s Fury Beast EXPO",
        url="https://www.pccomponentes.com/memoria-ram-kingston-32gb-2x16gb-ddr5-6000mt-s-fury-beast-expo-black",
        source="pccomponentes",
        target_price=90.0,
        category="ram",
        notes="Versión con AMD EXPO nativo — mejor para AM5. Activar perfil EXPO en BIOS.",
    ),

    # ─── Fuente de alimentación — versión ATX 3.1 / PCIe 5.1 (más moderna) ──
    # URL verificada ✅
    Product(
        id=None,
        name="Seasonic Focus GX-1000 ATX3 PCIe5.1 1000W Gold",
        url="https://www.pccomponentes.com/fuente-alimentacion-seasonic-focus-gx-1000-atx-3-pcie-51-1000w-80-plus-gold-modular",
        source="pccomponentes",
        target_price=160.0,
        category="psu",
        notes="ATX 3.1 + PCIe 5.1. 1000W para 2x 3090 futuro. 10 años garantía Seasonic.",
    ),

    # ─── SSD ─────────────────────────────────────────────────────────────────
    # URL verificada ✅
    Product(
        id=None,
        name="WD Black SN850X 1TB NVMe PCIe Gen4",
        url="https://www.pccomponentes.com/disco-duro-wd-black-sn850x-1tb-disco-ssd-7300mb-s-nvme-pcie-40-m2-gen4-16gt-s",
        source="pccomponentes",
        target_price=75.0,
        category="ssd",
        notes="7300MB/s lectura. Sin disipador (la X670E ya tiene disipadores M.2 integrados).",
    ),

    # ─── Caja ─────────────────────────────────────────────────────────────────
    # Fractal Design Pop Air — airflow excelente para la 3090
    Product(
        id=None,
        name="Fractal Design Pop Air ATX",
        url="https://www.pccomponentes.com/fractal-design-pop-air-negro",
        source="pccomponentes",
        target_price=65.0,
        category="case",
        notes="Buen airflow frontal para la 3090. Alternativa: Lian Li Lancool 216.",
    ),
]


if __name__ == "__main__":
    init_db()
    for p in PRODUCTS:
        pid = upsert_product(p)
        print(f"✅  [{p.category.upper():5}] {p.name[:55]:<55} | objetivo: {p.target_price:>6.0f}€ | fuente: {p.source}")

    print(f"\n{len(PRODUCTS)} productos cargados. Ejecuta 'python tracker.py' para el primer ciclo.")