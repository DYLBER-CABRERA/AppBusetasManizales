"""API pública del módulo pasajero."""

from modulos.pasajero.aplicacion.casos_de_uso import (
    AgregarFavorito,
    CrearAlertaLlegada,
    EliminarAlerta,
    EvaluarAlertasPorPosicion,
    ListarAlertas,
    ListarFavoritos,
    QuitarFavorito,
)
from modulos.pasajero.infraestructura.repositorio_sql import RepositorioAlertasSql, RepositorioFavoritosSql
from modulos.pasajero.infraestructura.router import router

__all__ = [
    "AgregarFavorito", "CrearAlertaLlegada", "EliminarAlerta", "EvaluarAlertasPorPosicion", "ListarAlertas",
    "ListarFavoritos", "QuitarFavorito", "RepositorioAlertasSql", "RepositorioFavoritosSql", "router",
]
