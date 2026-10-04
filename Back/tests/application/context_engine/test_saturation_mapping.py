"""Mapeo `occupancy_ratio` -> `saturation_level` en el ensamblaje de `ZoneState`.

Por que existe
--------------
Los modelos especializados emiten `occupancy_ratio` (y `free_ratio`,
`free_spaces`), pero `derive_zone_states` leia `model_data["saturation_level"]`,
una clave que ParkingV1 y BathroomV1 no producen. Con models conectados, ese
`None` se seguia propagando hasta la respuesta HTTP y la UI no veia ningun
cambio. Este archivo fija la regla de resolucion.
"""
from __future__ import annotations

import pytest

from src.application.context_engine.stage4_zone_state_derivation import (
    _resolve_saturation_level,
)


class TestResolucionDeSaturacion:
    def test_sin_modelo_devuelve_none(self):
        assert _resolve_saturation_level(None) is None

    def test_modelo_sin_ninguna_de_las_dos_claves_devuelve_none(self):
        assert _resolve_saturation_level({"occupied": 12.0, "capacity": 100}) is None

    def test_mapa_occupancy_ratio(self):
        """El caso que motiva el cambio: ParkingV1 emite `occupancy_ratio`."""
        assert _resolve_saturation_level({"occupancy_ratio": 0.866}) == pytest.approx(0.866)

    def test_respeta_la_clave_del_contrato_si_existe(self):
        """Compatibilidad hacia adelante: un modelo futuro que emita
        `saturation_level` no pasa por el alias."""
        assert _resolve_saturation_level({"saturation_level": 0.25}) == pytest.approx(0.25)

    def test_si_coexisten_manda_la_clave_del_contrato(self):
        """El alias es un fallback, no una mezcla. Con las dos claves, gana
        `saturation_level`."""
        assert _resolve_saturation_level(
            {"saturation_level": 0.25, "occupancy_ratio": 0.99}
        ) == pytest.approx(0.25)

    def test_cero_es_un_valor_valido(self):
        """0 no es "sin dato". Una zona vacia tiene saturacion 0 y la UI la
        tiene que distinguir de `None`."""
        assert _resolve_saturation_level({"occupancy_ratio": 0.0}) == pytest.approx(0.0)

    def test_acepta_entero(self):
        assert _resolve_saturation_level({"occupancy_ratio": 1}) == pytest.approx(1.0)

    @pytest.mark.parametrize("basura", [True, False, "0.8", None, [0.5], {"a": 1}])
    def test_rechaza_valores_no_numericos(self, basura):
        """Un `True` es un `int` en Python. Sin este filtro, `saturation_level`
        seria `True` y la UI lo pintaria como 100%."""
        assert _resolve_saturation_level({"occupancy_ratio": basura}) is None

    def test_diccionario_vacio_devuelve_none(self):
        assert _resolve_saturation_level({}) is None


class TestContratoConADR004:
    def test_no_deriva_de_projected_density(self):
        """ADR-004 §2.3/§2.4: el Context Engine NO genera un `saturation_level`
        universal. Esta funcion solo transporta lo que un modelo emitio; no
        recibe `projected_density` ni `capacity` y no puede derivarlos.

        Es un test de firma a proposito: si alguien agrega un parametro para
        calcularlo, este test sigue pasando pero la regla se rompio, asi que
        tambien se deja escrito por que la funcion no los recibe.
        """
        import inspect

        params = list(inspect.signature(_resolve_saturation_level).parameters)
        assert params == ["model_data"], (
            f"la firma cambio a {params}: si se agregara `projected_density` o "
            "`capacity` para calcular la saturacion, se violaria ADR-004 §2.3"
        )