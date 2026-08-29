import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")

# Portuguese Olist category -> English
translation_map = {
    "agro_industria_e_comercio": "agriculture_industry_and_commerce",
    "alimentos": "food",
    "alimentos_bebidas": "food_and_beverages",
    "artes": "arts",
    "artes_e_artesanato": "arts_and_crafts",
    "artigos_de_festas": "party_supplies",
    "artigos_de_natal": "christmas_supplies",
    "audio": "audio",
    "automotivo": "automotive",
    "bebes": "baby",
    "bebidas": "beverages",
    "beleza_saude": "health_beauty",
    "brinquedos": "toys",
    "cama_mesa_banho": "bed_bath_table",
    "casa_conforto": "home_comfort",
    "casa_conforto_2": "home_comfort_2",
    "casa_construcao": "home_construction",
    "cds_dvds_musicais": "cds_dvds_musicals",
    "cine_foto": "cinema_photo",
    "climatizacao": "climate_control",
    "consoles_games": "consoles_games",
    "construcao_ferramentas_construcao": "construction_tools",
    "construcao_ferramentas_ferramentas": "tools",
    "construcao_ferramentas_iluminacao": "construction_tools_lighting",
    "construcao_ferramentas_jardim": "garden_tools",
    "construcao_ferramentas_seguranca": "construction_tools_safety",
    "cool_stuff": "cool_stuff",
    "dvds_blu_ray": "dvds_blu_ray",
    "eletrodomesticos": "home_appliances",
    "eletrodomesticos_2": "home_appliances_2",
    "eletronicos": "electronics",
    "eletroportateis": "small_appliances",
    "esporte_lazer": "sports_leisure",
    "fashion_bolsas_e_acessorios": "fashion_bags_accessories",
    "fashion_calcados": "fashion_shoes",
    "fashion_esporte": "fashion_sports",
    "fashion_roupa_feminina": "womens_fashion",
    "fashion_roupa_infanto_juvenil": "childrens_fashion",
    "fashion_roupa_masculina": "mens_fashion",
    "fashion_underwear_e_moda_praia": "underwear_beachwear",
    "ferramentas_jardim": "garden_tools",
    "flores": "flowers",
    "fraldas_higiene": "diapers_hygiene",
    "industria_comercio_e_negocios": "industry_commerce_business",
    "informatica_acessorios": "computers_accessories",
    "instrumentos_musicais": "musical_instruments",
    "la_cuisine": "kitchen",
    "livros_importados": "imported_books",
    "livros_interesse_geral": "general_interest_books",
    "livros_tecnicos": "technical_books",
    "malas_acessorios": "luggage_accessories",
    "market_place": "marketplace",
    "moveis_colchao_e_estofado": "mattress_upholstery",
    "moveis_cozinha_area_de_servico_jantar_e_jardim": "kitchen_laundry_dining_garden_furniture",
    "moveis_decoracao": "furniture_decor",
    "moveis_escritorio": "office_furniture",
    "moveis_quarto": "bedroom_furniture",
    "moveis_sala": "living_room_furniture",
    "musica": "music",
    "papelaria": "stationery",
    "pc_gamer": "gaming_pc",
    "pcs": "pcs",
    "perfumaria": "perfumery",
    "pet_shop": "pet_shop",
    "portateis_casa_forno_e_cafe": "portable_home_appliances",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_appliances",
    "relogios_presentes": "watches_gifts",
    "seguros_e_servicos": "insurance_services",
    "sinalizacao_e_seguranca": "signaling_security",
    "tablets_impressao_imagem": "tablets_printing_image",
    "telefonia": "telephony",
    "telefonia_fixa": "fixed_telephony",
    "utilidades_domesticas": "household_utilities",
}

# Read categories actually present in our dataset
products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")

categories = set(
    products["product_category_name"]
    .dropna()
    .unique()
)

# Check that every category has a translation
missing = categories - translation_map.keys()

if missing:
    print("ERROR: Missing translations:")
    for category in sorted(missing):
        print(category)
    raise SystemExit(1)

# Create translation dataframe
translation = pd.DataFrame(
    [
        {
            "product_category_name": category,
            "product_category_name_english": translation_map[category],
        }
        for category in sorted(categories)
    ]
)

# Save file
output_path = DATA_DIR / "product_category_name_translation.csv"
translation.to_csv(output_path, index=False)

print(f"Translation file created: {output_path}")
print(f"Categories translated: {len(translation)}")
print("\nFirst 10 translations:")
print(translation.head(10))