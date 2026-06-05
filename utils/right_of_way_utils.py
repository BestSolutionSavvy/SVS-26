import carla
import math
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum


class ProximityStatus(Enum):
    CLEAR = "clear"
    WARNING = "warning"
    VIOLATION = "violation"


@dataclass
class ZoneConfig:
    """
    Parametri delle zone di rilevamento nel sistema di riferimento locale
    del veicolo ego (forward = +X, right = +Y).

    Le zone si estendono nella direzione right-forward (quadrante destra-avanti).
    """
    # Warning zone (rettangolo esterno, arancione)
    warn_forward_offset: float = 0.0    # offset dal centro del veicolo in avanti [m]
    warn_lateral_offset: float = 0.5    # offset laterale verso destra [m]
    warn_length: float = 12.0           # estensione in avanti [m]
    warn_width: float = 4.0             # estensione laterale [m]

    # Violation zone (rettangolo interno, rosso)
    viol_forward_offset: float = 2.0    # offset in avanti [m]
    viol_lateral_offset: float = 0.5    # offset laterale verso destra [m]
    viol_length: float = 6.0            # estensione in avanti [m]
    viol_width: float = 2.5             # estensione laterale [m]

    check_z_range: float = 2.0          # tolleranza verticale [m]


@dataclass
class ZoneCheckResult:
    status: ProximityStatus
    warning_vehicles: List[carla.Actor]
    violation_vehicles: List[carla.Actor]


def _world_to_local(
    ego_transform: carla.Transform,
    actor_location: carla.Location
) -> Tuple[float, float, float]:
    """
    Trasforma una posizione world-space nel sistema di riferimento locale
    dell'ego (forward=+X, right=+Y, up=+Z).
    """
    dx = actor_location.x - ego_transform.location.x
    dy = actor_location.y - ego_transform.location.y
    dz = actor_location.z - ego_transform.location.z

    yaw_rad = math.radians(ego_transform.rotation.yaw)
    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)

    # Rotazione inversa: proietta il delta nel frame locale
    local_x = cos_yaw * dx + sin_yaw * dy   # forward
    local_y = -sin_yaw * dx + cos_yaw * dy  # right (left = negativo)

    return local_x, local_y, dz


def _point_in_rect(
    local_x: float,
    local_y: float,
    forward_offset: float,
    lateral_offset: float,
    length: float,
    width: float,
) -> bool:
    """
    Controlla se un punto (local_x, local_y) è all'interno del rettangolo
    definito nel sistema di riferimento locale.

    Il rettangolo occupa:
        X in [forward_offset, forward_offset + length]
        Y in [lateral_offset, lateral_offset + width]
    """
    in_x = forward_offset <= local_x <= forward_offset + length
    in_y = lateral_offset <= local_y <= lateral_offset + width
    return in_x and in_y


def check_right_forward_zones(
    ego_vehicle: carla.Actor,
    world: carla.World,
    config: ZoneConfig = None,
) -> ZoneCheckResult:
    """
    Controlla la presenza di veicoli nelle zone destra-frontale dell'ego.

    Parametri
    ---------
    ego_vehicle : carla.Actor
        Il veicolo ego di riferimento.
    world : carla.World
        Il mondo CARLA corrente.
    config : ZoneConfig, optional
        Configurazione delle dimensioni delle zone. Usa i valori di default se None.

    Ritorna
    -------
    ZoneCheckResult
        Contiene lo stato complessivo (CLEAR / WARNING / VIOLATION) e le liste
        di veicoli rilevati in ciascuna zona.
    """
    if config is None:
        config = ZoneConfig()

    ego_transform = ego_vehicle.get_transform()
    ego_id = ego_vehicle.id

    # Recupera tutti i veicoli dalla scena (escluso l'ego)
    all_vehicles: List[carla.Actor] = [
        a for a in world.get_actors().filter("vehicle.*")
        if a.id != ego_id
    ]

    warning_vehicles: List[carla.Actor] = []
    violation_vehicles: List[carla.Actor] = []

    for vehicle in all_vehicles:
        actor_loc = vehicle.get_location()
        lx, ly, lz = _world_to_local(ego_transform, actor_loc)

        # Filtra per range verticale (evita veicoli su piani diversi)
        if abs(lz) > config.check_z_range:
            continue

        in_violation = _point_in_rect(
            lx, ly,
            config.viol_forward_offset,
            config.viol_lateral_offset,
            config.viol_length,
            config.viol_width,
        )

        in_warning = _point_in_rect(
            lx, ly,
            config.warn_forward_offset,
            config.warn_lateral_offset,
            config.warn_length,
            config.warn_width,
        )

        if in_violation:
            violation_vehicles.append(vehicle)
        elif in_warning:
            # Nella warning solo se NON già in violation (evita duplicati)
            warning_vehicles.append(vehicle)

    # Determina lo stato complessivo (priorità: violation > warning > clear)
    if violation_vehicles:
        status = ProximityStatus.VIOLATION
    elif warning_vehicles:
        status = ProximityStatus.WARNING
    else:
        status = ProximityStatus.CLEAR

    return ZoneCheckResult(
        status=status,
        warning_vehicles=warning_vehicles,
        violation_vehicles=violation_vehicles,
    )