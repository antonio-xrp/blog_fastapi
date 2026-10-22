import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

# Carpeta donde se guardan las fotos de perfil (relativa a donde ejecutas la app)
PROFILE_PICS_DIR = Path("media/profile_pics")


def process_profile_image(content: bytes) -> str:
    """Redimensiona la imagen, la guarda en disco y devuelve solo el nombre del archivo."""
    # Si el contenido no es una imagen, Image.open lanza UnidentifiedImageError,
    # que el router ya captura y convierte en un 400.
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)

        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"

        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)  # crea la carpeta si no existe
        img.save(PROFILE_PICS_DIR / filename, "JPEG", quality=85, optimize=True)

    return filename


def delete_profile_image(filename: str | None) -> None:
    """Borra la foto del disco. Síncrona, porque el router la llama sin await."""
    if filename is None:
        return
    # Path(filename).name descarta cualquier ruta ("../") y deja solo el nombre
    (PROFILE_PICS_DIR / Path(filename).name).unlink(missing_ok=True)