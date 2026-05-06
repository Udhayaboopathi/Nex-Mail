from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import PgpKey

router = APIRouter(tags=["pgp"])


class PgpKeyItem(BaseModel):
    mailbox_id: str
    public_key: str
    fingerprint: str | None = None
    is_enabled: bool


class GenerateKeyRequest(BaseModel):
    mailbox_id: str
    passphrase: str | None = None


@router.post("/generate", response_model=PgpKeyItem)
async def generate_pgp_key(payload: GenerateKeyRequest, user: dict = Depends(require_any_auth)) -> PgpKeyItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc

    try:
        import pgpy
        key = pgpy.PGPKey.new(pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 2048)
        uid = pgpy.PGPUID.new("Nex Mail User")
        key.add_uid(uid, usage={pgpy.constants.KeyFlags.Sign, pgpy.constants.KeyFlags.EncryptCommunications},
                    hashes=[pgpy.constants.HashAlgorithm.SHA256],
                    ciphers=[pgpy.constants.SymmetricKeyAlgorithm.AES256],
                    compression=[pgpy.constants.CompressionAlgorithm.ZLIB])
        public_key_str = str(key.pubkey)
        fingerprint = key.fingerprint.keyid
    except Exception:
        public_key_str = "PGP generation unavailable"
        fingerprint = None

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(PgpKey).where(PgpKey.mailbox_id == mailbox_uuid))).scalar_one_or_none()
        if existing:
            existing.public_key = public_key_str
            existing.fingerprint = fingerprint
            existing.is_enabled = True
            await db.commit()
            await db.refresh(existing)
            rec = existing
        else:
            rec = PgpKey(mailbox_id=mailbox_uuid, public_key=public_key_str, fingerprint=fingerprint, is_enabled=True)
            db.add(rec)
            await db.commit()
            await db.refresh(rec)
    return PgpKeyItem(mailbox_id=str(rec.mailbox_id), public_key=rec.public_key or "", fingerprint=rec.fingerprint, is_enabled=bool(rec.is_enabled))


@router.get("/own-key", response_model=PgpKeyItem)
async def get_own_pgp_key(user: dict = Depends(require_any_auth)) -> PgpKeyItem:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(PgpKey).where(PgpKey.is_enabled == True).limit(1))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No PGP key found")
    return PgpKeyItem(mailbox_id=str(row.mailbox_id), public_key=row.public_key or "", fingerprint=row.fingerprint, is_enabled=bool(row.is_enabled))


@router.get("/lookup/{email}", response_model=PgpKeyItem)
async def lookup_pgp_key(email: str, user: dict = Depends(require_any_auth)) -> PgpKeyItem:
    raise HTTPException(status_code=404, detail="No public key found for this address")


@router.delete("/own-key")
async def delete_own_pgp_key(user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    return {"ok": True}
