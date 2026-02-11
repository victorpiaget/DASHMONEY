#route API qui qui dedamnde au serveur s'il tourne bien


from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
