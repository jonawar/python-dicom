"""Random dummy-data pools and helpers for radiology records."""
import random

FIRST_M = ["BUDI", "AGUS", "RIZKI", "DONI", "HENDRA", "FAISAL", "YOGA", "ILHAM"]
FIRST_F = ["SARI", "DEWI", "PUTRI", "NISA", "RINA", "INTAN", "MAYA", "LIA"]
LAST = ["SANTOSO", "WIBOWO", "PRATAMA", "NUGROHO", "HIDAYAT", "MAHARANI",
        "ANGGRAINI", "PERMATA"]
INSTITUTIONS = ["RS Dummy", "RS Sehat Sentosa", "RS Cahaya Medika", "RS Bersama Kita"]
DEPARTMENTS = ["Radiologi", "UGD", "ICU", "Penyakit Dalam"]
LOCATIONS = ["RADIOLOGI", "ICU", "UGD", "RUANG CT"]
PHYSICIANS = ["DR Josh", "DR DUMMY", "DR Andi", "DR Lestari", "DR Bambang"]
MODALITIES = ["CT", "MR", "US", "DX"]
GUARANTORS = ["BPJS", "Mandiri Inhealth", "Prudential", "Allianz", "Self Pay"]

DESCRIPTIONS_BY_MOD = {
    "CT": ["CT TEST", "CT ABDOMEN", "CT KEPALA", "CT THORAX", "CT"],
    "MR": ["MRI BRAIN", "MRI SPINE", "MRI ABDOMEN", "MRI"],
    "US": ["USG ABDOMEN", "USG THYROID", "USG"],
    "DX": ["X-RAY THORAX", "X-RAY ABDOMEN", "FOTO THORAX"],
}
AE_BY_MOD = {
    "CT": ["CT01", "ct_pro", "CT02", "CTSCANNER"],
    "MR": ["MR01", "MR02"],
    "US": ["USG01", "US01"],
    "DX": ["DX01", "DR01"],
}


def pick(value, pool):
    """Return `value` unless it is 'random'/empty, then pick from pool."""
    return random.choice(pool) if value in ("random", "", None) else value


def random_name(sex: str):
    first = random.choice(FIRST_M if sex == "M" else FIRST_F)
    last = random.choice(LAST)
    return f"{last}^{first}", f"{first} {last}"


def random_birth_date():
    return (f"{random.randint(1970, 2005)}"
            f"{random.randint(1, 12):02d}{random.randint(1, 28):02d}")


def random_schedule_time(start_hour: int = 7, end_hour: int = 18):
    return (f"{random.randint(start_hour, end_hour):02d}"
            f"{random.randint(0, 59):02d}{random.randint(0, 59):02d}")
