import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv

load_dotenv()

import aiohttp
from backend_client import backend_client

async def main():
    token = await backend_client._get_valid_token("6475387133")
    if not token:
        print("Token olib bo‘lmadi!")
        return

    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        # 1. Marketplace listings
        url = f"{backend_client.base_url}/api/v1/cargo/marketplace/listings/"
        print("=== 1. MARKETPLACE LISTINGS ===")
        async with session.get(url, headers=headers) as resp:
            print("Status:", resp.status)
            data = await resp.json()
            if isinstance(data, dict):
                results = data.get("results", data)
                count = data.get("count", len(results) if isinstance(results, list) else 0)
                print(f"Jami yuklar soni (count): {count}")
            elif isinstance(data, list):
                results = data
                print(f"Jami yuklar ro'yxati (list): {len(results)}")
            else:
                results = []
                print("Noma'lum format:", type(data))

            print(f"\n--- YUKLAR RO'YXATI ({len(results)} ta) ---")
            for idx, item in enumerate(results, 1):
                item_id = item.get("id")
                status = item.get("status")
                orig = item.get("origin")
                dest = item.get("destination")
                price = item.get("price")
                curr = item.get("currency", "UZS")
                negotiable = item.get("price_negotiable")
                c_type = item.get("cargo_type")
                weight = item.get("weight")
                volume = item.get("volume")
                body = item.get("body_type")
                l_date = item.get("loading_date")
                c_at = item.get("created_at")
                desc = item.get("description")
                print(f"\n[{idx}] ID: {item_id} | Holati: {status}")
                print(f"   Marshrut: {orig} ➡️ {dest}")
                print(f"   Narx: {price} {curr} (Kelishiladi: {negotiable})")
                print(f"   Yuk turi: {c_type} | Og'irlik: {weight} t | Hajm: {volume} m3")
                print(f"   Kuzov: {body} | Yuklash: {l_date} | Yaratilgan: {c_at}")
                print(f"   Tavsif: {desc}")
                # print any other interesting keys
                extra_keys = {k: v for k, v in item.items() if k not in ["id", "status", "origin", "destination", "price", "currency", "price_negotiable", "cargo_type", "weight", "volume", "body_type", "loading_date", "created_at", "description"]}
                if extra_keys:
                    print(f"   Qo'shimcha: {json.dumps(extra_keys, ensure_ascii=False)}")

        # 2. Check other cargo endpoints if any
        print("\n=== 2. BOSHQA CARGO ENDPOINTLARNI TEKSHIRISH ===")
        endpoints = [
            "/api/v1/cargo/loads/",
            "/api/v1/cargo/my-loads/",
            "/api/v1/cargo/orders/",
            "/api/v1/cargo/shipments/",
        ]
        for ep in endpoints:
            try:
                async with session.get(f"{backend_client.base_url}{ep}", headers=headers) as r:
                    print(f"Endpoint: {ep} -> Status: {r.status}")
                    if r.status == 200:
                        res = await r.json()
                        c = res.get("count", len(res)) if isinstance(res, (dict, list)) else "N/A"
                        print(f"   Natija: {c} ta ma'lumot")
            except Exception as e:
                print(f"   Xatolik: {ep}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
