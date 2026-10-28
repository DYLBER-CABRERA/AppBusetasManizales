from __future__ import annotations

from datetime import time

import pytest

from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorConflictoVersion
from nucleo.registro import ocultar_sensibles
from nucleo.reloj import RelojSimulado
from nucleo.version_optimista import verificar_version


def test_version_distinta_lanza_conflicto() -> None:
    with pytest.raises(ErrorConflictoVersion) as e:
        verificar_version(1, 3)
    assert e.value.estado_http == 409
    assert e.value.detalles == {"versionActual": 3}


def test_version_igual_pasa() -> None:
    verificar_version(2, 2)


def test_reloj_simulado_fija_y_restaura() -> None:
    reloj = RelojSimulado()
    reloj.fijar_hora(time(6, 30))
    assert (reloj.ahora().hour, reloj.ahora().minute) == (6, 30)
    assert str(reloj.ahora().tzinfo) == "America/Bogota"
    reloj.fijar_hora(None)
    assert reloj.ahora().second >= 0


def test_filtro_oculta_secretos_y_datos_personales() -> None:
    texto = ocultar_sensibles(
        "Authorization: Bearer abc.def X-Clave-Fuente=zzz correo ana@correo.example lat=5.07 lng=-75.5"
    )
    for prohibido in ("abc.def", "zzz", "ana@correo.example", "5.07", "75.5"):
        assert prohibido not in texto


def test_festivos_se_leen_de_configuracion() -> None:
    c = Configuracion(festivos="2026-11-02, 2026-12-25")
    assert len(c.lista_festivos) == 2


def test_festivo_invalido_falla() -> None:
    with pytest.raises(ValueError):
        Configuracion(festivos="no-es-fecha")
