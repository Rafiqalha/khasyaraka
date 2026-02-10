#!/usr/bin/env python3
"""
Sandi Pramuka Data Seeding Script

Seeds the database with 15 Sandi Pramuka types.
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.cyber.models import SandiType, SandiCategory


# 15 Sandi Pramuka definitions
SANDI_DATA = [
    {
        "codename": "morse",
        "name": "Morse",
        "description": "Sandi Morse menggunakan titik (.) dan garis (-) untuk menyandikan huruf dan angka.",
        "difficulty": 1,
        "category": SandiCategory.encoding
    },
    {
        "codename": "semaphore",
        "name": "Semaphore",
        "description": "Sandi Semaphore menggunakan bendera untuk menyampaikan pesan dengan posisi tangan.",
        "difficulty": 2,
        "category": SandiCategory.visual
    },
    {
        "codename": "rumput",
        "name": "Rumput",
        "description": "Sandi Rumput menggunakan bentuk huruf yang menyerupai rumput untuk menyembunyikan pesan.",
        "difficulty": 2,
        "category": SandiCategory.visual
    },
    {
        "codename": "kimia",
        "name": "Kimia",
        "description": "Sandi Kimia menggunakan simbol-simbol kimia untuk menyandikan pesan.",
        "difficulty": 3,
        "category": SandiCategory.substitution
    },
    {
        "codename": "angka",
        "name": "Angka",
        "description": "Sandi Angka menggantikan huruf dengan angka sesuai urutan alfabet.",
        "difficulty": 1,
        "category": SandiCategory.substitution
    },
    {
        "codename": "an_rot13",
        "name": "AN (ROT13)",
        "description": "Sandi AN atau ROT13 menggeser setiap huruf 13 posisi dalam alfabet (Caesar cipher).",
        "difficulty": 1,
        "category": SandiCategory.substitution
    },
    {
        "codename": "az_atbash",
        "name": "AZ (Atbash)",
        "description": "Sandi AZ atau Atbash membalikkan alfabet (A=Z, B=Y, C=X, dst).",
        "difficulty": 1,
        "category": SandiCategory.substitution
    },
    {
        "codename": "kotak_1",
        "name": "Kotak 1",
        "description": "Sandi Kotak 1 menggunakan grid 5x5 untuk menyandikan pesan.",
        "difficulty": 2,
        "category": SandiCategory.transposition
    },
    {
        "codename": "kotak_2",
        "name": "Kotak 2",
        "description": "Sandi Kotak 2 menggunakan variasi grid untuk menyandikan pesan.",
        "difficulty": 2,
        "category": SandiCategory.transposition
    },
    {
        "codename": "kotak_3",
        "name": "Kotak 3",
        "description": "Sandi Kotak 3 menggunakan grid kompleks untuk menyandikan pesan.",
        "difficulty": 3,
        "category": SandiCategory.transposition
    },
    {
        "codename": "jam",
        "name": "Jam",
        "description": "Sandi Jam menggunakan posisi jarum jam untuk menyandikan huruf.",
        "difficulty": 2,
        "category": SandiCategory.visual
    },
    {
        "codename": "koordinat",
        "name": "Koordinat",
        "description": "Sandi Koordinat menggunakan sistem koordinat (baris, kolom) untuk menyandikan pesan.",
        "difficulty": 2,
        "category": SandiCategory.substitution
    },
    {
        "codename": "and",
        "name": "AND",
        "description": "Sandi AND menggunakan operasi logika AND untuk menyandikan pesan.",
        "difficulty": 3,
        "category": SandiCategory.substitution
    },
    {
        "codename": "ular",
        "name": "Ular",
        "description": "Sandi Ular menggunakan pola zigzag seperti ular untuk menyandikan pesan.",
        "difficulty": 2,
        "category": SandiCategory.transposition
    },
    {
        "codename": "napoleon",
        "name": "Napoleon",
        "description": "Sandi Napoleon menggunakan metode enkripsi yang dikembangkan pada era Napoleon.",
        "difficulty": 3,
        "category": SandiCategory.transposition
    }
]


async def create_tables():
    """Create database tables if they don't exist"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_sandi_types(session: AsyncSession):
    """Seed Sandi types into database"""
    print("Seeding Sandi Pramuka types...")
    
    created_count = 0
    updated_count = 0
    
    for sandi_data in SANDI_DATA:
        # Check if Sandi type already exists
        result = await session.execute(
            select(SandiType).where(SandiType.codename == sandi_data["codename"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.name = sandi_data["name"]
            existing.description = sandi_data["description"]
            existing.difficulty = sandi_data["difficulty"]
            existing.category = sandi_data["category"]
            updated_count += 1
            print(f"  Updated: {sandi_data['codename']} - {sandi_data['name']}")
        else:
            # Create new
            sandi_type = SandiType(**sandi_data)
            session.add(sandi_type)
            created_count += 1
            print(f"  Created: {sandi_data['codename']} - {sandi_data['name']}")
    
    await session.commit()
    
    print(f"\n✅ Seeding complete!")
    print(f"   Created: {created_count} Sandi types")
    print(f"   Updated: {updated_count} Sandi types")
    print(f"   Total: {len(SANDI_DATA)} Sandi types")


async def main():
    """Main seeding function"""
    await create_tables()
    async with SessionLocal() as session:
        await seed_sandi_types(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
