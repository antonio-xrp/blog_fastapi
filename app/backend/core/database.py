from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

#administra la comunicación con la base de datos
# utiliza una pool de conexiones cuando corresponde
engine = create_async_engine(settings.database_url)

#Fabrica de sesiones asíncronas
#  expire_on_commit=False : Permite acceder a los atributos
# ya cargados de los objetos despues de un commit()
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Clase madre de todos los modelos.
class Base(DeclarativeBase):
    pass


# Permite proporcionar una sesion a los endpoints y cerrar
# sesion cuando termine su ciclo de vida. Para persistir cambios 
# se debe ejecutar un await db.commit() en los endpoints.
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Alias para inyectar la sesión en los routers sin repetir Annotated/Depends
DbSession = Annotated[AsyncSession, Depends(get_db)]