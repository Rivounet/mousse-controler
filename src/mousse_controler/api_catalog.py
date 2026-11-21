"""Declarative API, action and WebSocket contracts used by routing and discovery."""

from __future__ import annotations

import copy
import json
from typing import Any


CONTRACT_VERSION = "1.0.0"
API_PATH = "/v1/command"


def _parameter(
    value_type: str,
    description: str,
    *,
    required: bool = False,
    default: Any = None,
    allowed: list[Any] | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": value_type,
        "description": description,
        "required": required,
    }
    if default is not None:
        result["default"] = default
    if allowed is not None:
        result["allowed_values"] = allowed
    if constraints:
        result["constraints"] = constraints
    return result


def _request(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "command_id": f"example-{name}",
        "issued_at_ms": 1_700_000_000_000,
        "ttl_ms": 5_000,
        "command": name,
        "arguments": arguments or {},
    }


def _command(
    name: str,
    description: str,
    category: str,
    handler: str,
    *,
    parameters: dict[str, dict[str, Any]] | None = None,
    example_arguments: dict[str, Any] | None = None,
    example_response: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    effects: list[str] | None = None,
    events: list[str] | None = None,
    dynamic_constraints: list[str] | None = None,
    requirement: str | None = None,
) -> dict[str, Any]:
    response_example = example_response or {"accepted": True, "command": name}
    return {
        "resource_type": "api_command",
        "name": name,
        "description": description,
        "category": category,
        "parameters": parameters or {},
        "additional_parameters_allowed": True,
        "static_constraints": [
            "Authenticated POST envelope with a unique command_id.",
            "ttl_ms must be between 1 and 5000; issued_at_ms may be at most 1000 ms in the future.",
        ],
        "dynamic_constraints": dynamic_constraints or [],
        "examples": {
            "request": _request(name, example_arguments),
            "response": response_example,
        },
        "response": {"type": "object", "example": copy.deepcopy(response_example)},
        "errors": errors or [],
        "effects": effects or [],
        "events": events or [],
        "availability": {
            "status": "available",
            "requirement": requirement,
            "version": CONTRACT_VERSION,
        },
        "contract_version": CONTRACT_VERSION,
        "_handler": handler,
    }


ACTION_ID = _parameter("string", "Identifiant de l'action.", required=True,
                       constraints={"min_length": 1, "max_length": 128})
LIMIT = _parameter("integer", "Nombre maximal d'éléments retournés.", default=100,
                   constraints={"minimum": 1, "maximum": 500})
BUTTON_NAMES = ["left", "right", "middle", "back", "forward"]


COMMAND_CONTRACTS: dict[str, dict[str, Any]] = {}


def _insert_unique(
    registry: dict[str, dict[str, Any]], contract: dict[str, Any], resource: str,
) -> None:
    name = contract["name"]
    if name in registry:
        raise ValueError(f"duplicate {resource} contract: {name}")
    registry[name] = contract


def _add(contract: dict[str, Any]) -> None:
    _insert_unique(COMMAND_CONTRACTS, contract, "command")


_add(_command(
    "api_catalog", "Découvre les commandes, types d'actions et événements WebSocket.",
    "discovery", "_command_api_catalog",
    parameters={
        "name": _parameter("string", "Nom exact d'une commande à rechercher.",
                           constraints={"min_length": 1, "max_length": 128}),
        "category": _parameter("string", "Catégorie exacte à filtrer."),
        "include": _parameter(
            "array", "Sections à inclure.",
            default=["commands", "action_types", "websocket_events"],
            allowed=["commands", "action_types", "websocket_events"],
            constraints={"min_items": 1, "unique_items": True},
        ),
    },
    example_arguments={"category": "actions", "include": ["commands", "action_types"]},
    example_response={
        "accepted": True, "command": "api_catalog", "contract_version": CONTRACT_VERSION,
        "counts": {"commands": 8, "action_types": 12, "websocket_events": 0},
        "commands": [], "action_types": [],
    },
    errors=["unknown catalog command", "unknown catalog category", "invalid catalog section"],
))

_add(_command(
    "advertise_start", "Démarre l'annonce Bluetooth HOGP.", "bluetooth",
    "_command_advertise_start", effects=["Démarre ou redémarre l'annonce Bluetooth."],
    dynamic_constraints=["Le transport Bluetooth doit accepter la demande d'annonce."],
    errors=["transport unavailable"],
))
_add(_command(
    "transport_status", "Retourne l'état du transport Bluetooth.", "bluetooth",
    "_command_transport_status",
    example_response={"accepted": True, "command": "transport_status", "status": {}},
    errors=["transport status is unavailable"],
))
_add(_command(
    "position_status", "Retourne la dernière position distante utilisable.", "position",
    "_command_position_status",
    example_response={"accepted": True, "command": "position_status", "position": {
        "x": 100, "y": 200, "sequence": 4, "session_id": "session",
        "topology_generation": 1, "observed_at_unix_ms": 1_700_000_000_000, "age_ms": 12.5,
    }},
    dynamic_constraints=["La position doit être disponible et âgée d'au plus 5000 ms."],
    errors=["position unavailable", "position stale"],
))
_add(_command(
    "position_metrics", "Retourne les métriques du récepteur de position.", "position",
    "_command_position_metrics",
    example_response={"accepted": True, "command": "position_metrics", "metrics": {}},
    errors=["position metrics are unavailable"],
))

_add(_command(
    "move", "Déplace le pointeur d'un delta relatif (commande historique).", "mouse_legacy",
    "_command_move",
    parameters={
        "dx": _parameter("integer", "Déplacement horizontal relatif.", required=True,
                         constraints={"minimum": -32768, "maximum": 32767}),
        "dy": _parameter("integer", "Déplacement vertical relatif.", required=True,
                         constraints={"minimum": -32768, "maximum": 32767}),
    },
    example_arguments={"dx": 5, "dy": -3},
    effects=["Peut émettre un rapport HID de mouvement."], events=["state"],
    dynamic_constraints=["Le contrôleur et le transport HID doivent être opérationnels."],
    errors=["missing parameter", "controller stopped", "transport failure"],
))
_add(_command(
    "click", "Effectue un clic (commande historique).", "mouse_legacy", "_command_click",
    parameters={"button_bit": _parameter(
        "integer", "Bit du bouton HID.", required=True, allowed=[1, 2, 4, 8, 16])},
    example_arguments={"button_bit": 1}, effects=["Peut émettre deux rapports HID de bouton."],
    events=["state"], dynamic_constraints=["Le transport HID doit être opérationnel."],
    errors=["invalid button", "controller stopped", "transport failure"],
))
_add(_command(
    "buttons", "Fixe le masque des boutons (commande historique).", "mouse_legacy",
    "_command_buttons", parameters={
        "mask": _parameter("integer", "Masque HID cinq boutons.", required=True,
                           constraints={"minimum": 0, "maximum": 31})},
    example_arguments={"mask": 0}, effects=["Peut émettre un rapport HID de bouton."],
    events=["state"], errors=["invalid mask", "controller stopped", "transport failure"],
))
_add(_command(
    "scroll", "Fait défiler verticalement (commande historique).", "mouse_legacy",
    "_command_scroll", parameters={
        "delta": _parameter("integer", "Delta vertical HID.", required=True,
                            constraints={"minimum": -127, "maximum": 127})},
    example_arguments={"delta": -1}, effects=["Peut émettre un rapport HID de molette."],
    events=["state"], errors=["invalid delta", "controller stopped", "transport failure"],
))
_add(_command(
    "stop", "Déclenche l'arrêt d'urgence et relâche les boutons.", "supervision",
    "_command_stop", effects=["Annule les actions actives et relâche les boutons HID."],
    dynamic_constraints=["Best effort si le transport est déjà défaillant."],
))
_add(_command(
    "capabilities", "Retourne les capacités d'action et du descripteur HID.", "supervision",
    "_command_capabilities",
    example_response={"accepted": True, "command": "capabilities", "capabilities": {
        "buttons": {"left": 1, "right": 2, "middle": 4, "back": 8, "forward": 16},
        "vertical_wheel": True, "horizontal_wheel": False,
    }},
))

_add(_command(
    "action_submit", "Valide et soumet une action avancée.", "actions",
    "_command_action_submit", parameters={
        "action": _parameter("object", "Spécification d'un type d'action catalogué.", required=True),
        "action_id": _parameter("string", "Identifiant client optionnel et anti-rejeu.",
                                constraints={"min_length": 1, "max_length": 128}),
    },
    example_arguments={"action_id": "action-example", "action": {
        "kind": "wait", "duration_seconds": 0.1}},
    example_response={"accepted": True, "command": "action_submit", "action": {
        "action_id": "action-example", "kind": "wait", "state": "ACCEPTED"}},
    effects=["Ajoute une action à la file d'exécution; selon son type, elle peut produire du HID ou une capture."],
    events=["state", "retry", "capture", "result"],
    dynamic_constraints=["L'identifiant ne doit pas avoir été accepté pendant la durée de rétention.",
                         "Le moteur d'actions et sa file doivent être disponibles."],
    errors=["unknown action kind", "invalid action", "duplicate action id", "action queue capacity exceeded"],
    requirement="actions",
))
for action_name, description, handler in (
    ("action_status", "Retourne l'état courant d'une action.", "_command_action_status"),
    ("action_cancel", "Demande l'annulation d'une action.", "_command_action_cancel"),
    ("action_pause", "Met en pause une action active.", "_command_action_pause"),
    ("action_resume", "Reprend une action en pause.", "_command_action_resume"),
    ("action_continue", "Débloque une action wait_command.", "_command_action_continue"),
):
    _add(_command(
        action_name, description, "actions", handler,
        parameters={"action_id": copy.deepcopy(ACTION_ID)},
        example_arguments={"action_id": "action-example"},
        example_response={"accepted": True, "command": action_name,
                          "action" if action_name in {"action_status", "action_cancel"} else "event": {}},
        events=["state"] if action_name == "action_cancel" else (["control"] if action_name != "action_status" else []),
        dynamic_constraints=["L'action doit exister dans le registre actif."],
        errors=["unknown action id", "unknown or completed action id"], requirement="actions",
    ))
_add(_command(
    "action_list", "Liste les actions du registre actif.", "actions", "_command_action_list",
    parameters={"limit": copy.deepcopy(LIMIT)}, example_arguments={"limit": 20},
    example_response={"accepted": True, "command": "action_list", "actions": []},
    errors=["invalid action list limit"], requirement="actions",
))
_add(_command(
    "action_events", "Lit l'historique récent des événements d'action.", "actions",
    "_command_action_events", parameters={
        "after_event_id": _parameter("string", "Curseur d'événement optionnel."),
        "limit": copy.deepcopy(LIMIT),
    }, example_arguments={"limit": 20},
    example_response={"accepted": True, "command": "action_events", "events": []},
    errors=["invalid history limit"], requirement="actions",
))

_add(_command(
    "capture_status", "Liste les captures associées à une action.", "captures",
    "_command_capture_status", parameters={"action_id": copy.deepcopy(ACTION_ID)},
    example_arguments={"action_id": "action-example"},
    example_response={"accepted": True, "command": "capture_status", "captures": []},
    errors=["capture subsystem is unavailable"], requirement="captures",
))
_add(_command(
    "capture_delete", "Supprime de manière contrôlée une capture identifiée.", "captures",
    "_command_capture_delete", parameters={
        "capture_id": _parameter("string", "Identifiant de capture.", required=True,
                                 constraints={"min_length": 1, "max_length": 128})},
    example_arguments={"capture_id": "capture-example"},
    example_response={"accepted": True, "command": "capture_delete", "capture": {
        "capture_id": "capture-example", "state": "DELETED"}},
    effects=["Peut supprimer le fichier de capture désigné."],
    dynamic_constraints=["DELETED n'est retourné que lorsque l'absence du fichier est établie."],
    errors=["unknown capture id", "capture deletion failed"], requirement="captures",
))

ZONE_EXAMPLE = {"type": "rectangle", "x": 10, "y": 10, "width": 100, "height": 80}
_add(_command(
    "sequence_start", "Démarre une séquence géométrique de cibles.", "sequences",
    "_command_sequence_start", parameters={
        "steps": {**_parameter("array", "Étapes géométriques à exécuter.", required=True,
                               constraints={"min_items": 1}),
                  "item_contract": {
                      "zone": "rectangle(x,y,width,height), circle(center_x,center_y,radius) "
                              "ou polygon(vertices)",
                      "wait_mode": {"allowed_values": ["automatic", "commanded"],
                                    "default": "automatic"},
                      "wait_seconds": {"type": "number", "default": 0},
                  }},
        "trajectory": {**_parameter("object", "Configuration optionnelle de trajectoire."),
                       "properties": {
                           "spacing_px": {"type": "number", "default": 32.0,
                                          "minimum_exclusive": 0},
                           "curvature": {"type": "number", "default": 0.12,
                                         "minimum": -0.5, "maximum": 0.5},
                           "speed_variation": {"type": "number", "default": 0.04,
                                               "minimum": 0, "maximum": 0.15},
                           "micro_variation_px": {"type": "integer", "default": 1,
                                                  "minimum": 0, "maximum": 3},
                           "minimum_points": {"type": "integer", "default": 3, "minimum": 2},
                           "maximum_points": {"type": "integer", "default": 10},
                       }},
        "seed": _parameter("integer", "Graine déterministe optionnelle."),
    }, example_arguments={"steps": [{"zone": ZONE_EXAMPLE, "wait_mode": "automatic",
                                      "wait_seconds": 0}], "seed": 7},
    effects=["Peut déplacer le pointeur via le contrôleur HID."],
    dynamic_constraints=["Une seule séquence non terminale peut être active.",
                         "Les zones doivent appartenir à la topologie physique."],
    errors=["a sequence is already active", "unknown zone type", "invalid trajectory sampling"],
))
for sequence_name, description, handler in (
    ("sequence_pause", "Met en pause la séquence active.", "_command_sequence_pause"),
    ("sequence_resume", "Reprend la séquence active.", "_command_sequence_resume"),
    ("sequence_next", "Valide la cible manuelle courante.", "_command_sequence_next"),
    ("sequence_skip", "Ignore la cible courante.", "_command_sequence_skip"),
    ("sequence_stop", "Arrête la séquence active.", "_command_sequence_stop"),
):
    _add(_command(
        sequence_name, description, "sequences", handler,
        effects=["Modifie l'état de la séquence active."],
        dynamic_constraints=["Une séquence doit être active."], errors=["no sequence"],
    ))
_add(_command(
    "sequence_status", "Retourne l'état détaillé de la séquence active.", "sequences",
    "_command_sequence_status",
    example_response={"sequence_id": "sequence-example", "state": "RUNNING", "current_index": 0,
                      "target": None, "measured_position": None, "wait_mode": None,
                      "error": None, "started_at": 0.0, "updated_at": 0.0, "results": []},
    dynamic_constraints=["Une séquence doit avoir été créée."], errors=["no sequence"],
))


def _common_action_parameters(kind: str) -> dict[str, dict[str, Any]]:
    return {
        "kind": _parameter("string", "Discriminant du type d'action.", required=True, allowed=[kind]),
        "action_id": _parameter("string", "Identifiant optionnel d'une action enfant.",
                                constraints={"min_length": 1, "max_length": 128}),
        "error_policy": _parameter("string", "Politique en cas d'échec.", default="stop",
                                   allowed=["stop", "retry", "continue"]),
        "max_attempts": {**_parameter("integer", "Nombre maximal de tentatives.", default=1,
                                      constraints={"minimum": 1, "maximum": 3}),
                         "conditional_default": {"when": {"error_policy": "retry"}, "value": 2}},
        "capture": {**_parameter("object", "Capture avant/après optionnelle pour les actions souris."),
                    "properties": {
                        "before": {"type": "boolean", "default": False},
                        "after": {"type": "boolean", "default": False},
                        "retention_seconds": {"type": "integer", "default": 86_400,
                                              "minimum": 0, "maximum": 2_592_000},
                        "timeout_seconds": {"type": "number", "default": 8.0},
                    }},
    }


def _action(
    kind: str,
    description: str,
    parameters: dict[str, dict[str, Any]],
    *,
    example: dict[str, Any],
    effects: list[str],
    dynamic: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    merged = _common_action_parameters(kind)
    merged.update(parameters)
    return {
        "resource_type": "action_type",
        "name": kind,
        "description": description,
        "category": "action_type",
        "parameters": merged,
        "additional_parameters_allowed": True,
        "static_constraints": [
            "max_attempts est compris entre 1 et 3.",
            "La capture, si présente, utilise une rétention de 0 à 2592000 secondes.",
        ],
        "dynamic_constraints": dynamic or [],
        "examples": {"request_fragment": example, "result": {"state": "EXECUTED"}},
        "response": {"type": "action_record", "terminal_states": [
            "EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED"]},
        "errors": errors or ["INVALID_ACTION", "ACTION_FAILED"],
        "effects": effects,
        "events": ["state", "retry", "capture", "result"],
        "availability": {"status": "available", "requirement": "actions",
                         "version": CONTRACT_VERSION},
        "contract_version": CONTRACT_VERSION,
    }


RELATIVE_COORDINATE = {"minimum": -32768, "maximum": 32767}
BUTTON = _parameter("string_or_integer", "Nom ou bit d'un bouton.", default="left",
                    allowed=BUTTON_NAMES + [1, 2, 4, 8, 16])
MASK = _parameter("integer", "Masque combiné des cinq boutons.", constraints={"minimum": 1, "maximum": 31})
ABSOLUTE = {
    "x": _parameter("integer", "Coordonnée physique X.", required=True),
    "y": _parameter("integer", "Coordonnée physique Y.", required=True),
    "tolerance_px": _parameter("integer", "Tolérance de confirmation.", default=2,
                               constraints={"minimum": 0}),
    "timeout_seconds": _parameter("number", "Délai de positionnement.", default=5.0,
                                  constraints={"minimum_exclusive": 0}),
}
BUTTON_MASK_PARAMETERS = {
    "button": copy.deepcopy(BUTTON),
    "mask": copy.deepcopy(MASK),
    "buttons": _parameter("array", "Liste non vide de noms/bits de boutons.",
                          constraints={"min_items": 1}),
}

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {}


def _add_action(contract: dict[str, Any]) -> None:
    _insert_unique(ACTION_CONTRACTS, contract, "action")


_add_action(_action("move_relative", "Déplacement relatif.", {
    "dx": _parameter("integer", "Delta X.", required=True, constraints=RELATIVE_COORDINATE),
    "dy": _parameter("integer", "Delta Y.", required=True, constraints=RELATIVE_COORDINATE),
}, example={"kind": "move_relative", "dx": 5, "dy": -3},
    effects=["Émet un rapport HID relatif."], errors=["MOVE_UNCERTAIN", "ACTION_FAILED"]))
_add_action(_action("move_to", "Positionnement absolu avec confirmation distante.", ABSOLUTE,
    example={"kind": "move_to", "x": 100, "y": 200},
    effects=["Peut émettre plusieurs rapports HID relatifs."],
    dynamic=["La position distante doit être fraîche et la cible sur la topologie physique."],
    errors=["POSITION_UNAVAILABLE", "POSITION_STALE", "ACTION_FAILED"]))
_add_action(_action("click", "Un ou plusieurs clics d'un bouton.", {
    "button": copy.deepcopy(BUTTON),
    "count": _parameter("integer", "Nombre de clics.", default=1,
                        constraints={"minimum": 1, "maximum": 20}),
    "hold_seconds": _parameter("number", "Durée d'appui.", default=0.04,
                               constraints={"minimum": 0, "maximum": 30}),
    "interval_seconds": _parameter("number", "Intervalle entre clics.", default=0.08,
                                   constraints={"minimum": 0, "maximum": 5}),
}, example={"kind": "click", "button": "left", "count": 1},
    effects=["Émet des rapports HID d'appui et relâchement."], errors=["CLICK_UNCERTAIN"]))
for kind in ("press", "release"):
    _add_action(_action(kind, f"{'Appuie' if kind == 'press' else 'Relâche'} un masque de boutons.",
        BUTTON_MASK_PARAMETERS, example={"kind": kind, "button": "left"},
        effects=["Émet un rapport HID de boutons."], errors=["BUTTON_UNCERTAIN"]))
_add_action(_action("hold", "Maintient puis relâche des boutons.", {
    **BUTTON_MASK_PARAMETERS,
    "duration_seconds": _parameter("number", "Durée du maintien.", required=True,
                                   constraints={"minimum": 0, "maximum": 30}),
}, example={"kind": "hold", "button": "left", "duration_seconds": 0.2},
    effects=["Émet des rapports HID d'appui et relâchement."], errors=["BUTTON_UNCERTAIN"]))
_add_action(_action("drag", "Glisser-déposer vers une position absolue.", {
    **BUTTON_MASK_PARAMETERS, **ABSOLUTE,
}, example={"kind": "drag", "button": "left", "x": 100, "y": 200},
    effects=["Appuie, déplace le pointeur puis relâche via HID."],
    dynamic=["La cible doit appartenir à la topologie physique."], errors=["DRAG_UNCERTAIN"]))
_add_action(_action("move_with_buttons", "Déplace avec un ou plusieurs boutons maintenus.", {
    **BUTTON_MASK_PARAMETERS,
    "x": _parameter("integer", "Coordonnée X en mode absolu."),
    "y": _parameter("integer", "Coordonnée Y en mode absolu."),
    "dx": _parameter("integer", "Delta X en mode relatif.", constraints=RELATIVE_COORDINATE),
    "dy": _parameter("integer", "Delta Y en mode relatif.", constraints=RELATIVE_COORDINATE),
    "tolerance_px": copy.deepcopy(ABSOLUTE["tolerance_px"]),
    "timeout_seconds": copy.deepcopy(ABSOLUTE["timeout_seconds"]),
}, example={"kind": "move_with_buttons", "button": "left", "dx": 5, "dy": 0},
    effects=["Appuie, déplace puis relâche via HID."],
    dynamic=["Fournir x et y ensemble, ou dx et dy ensemble."], errors=["DRAG_UNCERTAIN"]))
_add_action(_action("scroll", "Défilement borné ou continu.", {
    "axis": _parameter("string", "Axe demandé.", default="vertical",
                       allowed=["vertical", "horizontal"]),
    "delta": _parameter("integer", "Delta total du mode borné.", default=0,
                        constraints={"minimum": -63_500, "maximum": 63_500}),
    "duration_seconds": _parameter("number", "Durée du mode continu.",
                                   constraints={"minimum_exclusive": 0, "maximum": 30}),
    "interval_seconds": _parameter("number", "Intervalle du mode continu.", default=0.05,
                                   constraints={"minimum": 0.01, "maximum": 5}),
    "step": _parameter("integer", "Pas HID non nul du mode continu.", default=1,
                       constraints={"minimum": -127, "maximum": 127, "not": 0}),
}, example={"kind": "scroll", "delta": -3},
    effects=["Peut émettre jusqu'à 500 rapports HID de molette."],
    dynamic=["Le descripteur appairé ne permet actuellement que l'axe vertical."],
    errors=["CAPABILITY_UNAVAILABLE", "SCROLL_UNCERTAIN", "ACTION_LIMIT"]))
_add_action(_action("wait", "Attend une durée sans effet HID.", {
    "duration_seconds": _parameter("number", "Durée d'attente.", required=True,
                                   constraints={"minimum": 0, "maximum": 300}),
}, example={"kind": "wait", "duration_seconds": 0.1}, effects=["Aucun effet HID."]))
_add_action(_action("wait_command", "Attend une commande action_continue.", {
    "timeout_seconds": _parameter("number", "Délai maximal.", default=300,
                                  constraints={"minimum": 0.1, "maximum": 3600}),
}, example={"kind": "wait_command", "timeout_seconds": 30}, effects=["Aucun effet HID."],
    dynamic=["action_continue doit viser l'action active avant l'échéance."], errors=["WAIT_TIMEOUT"]))
_add_action(_action("sequence", "Exécute une liste ordonnée d'actions avancées.", {
    "actions": _parameter("array", "Actions enfants.", required=True,
                          constraints={"min_items": 1, "max_items": 256}),
}, example={"kind": "sequence", "actions": [{"kind": "wait", "duration_seconds": 0.1}]},
    effects=["Cumule les effets des actions enfants."],
    dynamic=["Chaque enfant est validé avec son propre contrat et reçoit un identifiant anti-rejeu."],
    errors=["SEQUENCE_CHILD_FAILED", "INVALID_ACTION"]))


WEBSOCKET_EVENT_CONTRACTS: dict[str, dict[str, Any]] = {}


def _add_event(contract: dict[str, Any]) -> None:
    _insert_unique(WEBSOCKET_EVENT_CONTRACTS, contract, "WebSocket event")


_EVENT_CONTRACTS = [
    {
        "resource_type": "websocket_event", "name": "connected",
        "description": "Message initial confirmant la connexion authentifiée.",
        "payload": {"event_type": "connected", "emitted_at_ms": 1_700_000_000_000,
                    "protocol": "mousse.actions.v1"},
        "produced_by": ["WebSocket handshake"], "effects": [], "contract_version": CONTRACT_VERSION,
    },
    {
        "resource_type": "websocket_event", "name": "state",
        "description": "Transition d'état d'une action.",
        "payload": {"event_id": "uuid", "event_type": "state", "emitted_at_ms": 0,
                    "action": {"action_id": "id", "state": "ACCEPTED"}},
        "produced_by": ["legacy commands", "action_submit", "action_cancel", "action execution"],
        "effects": [], "contract_version": CONTRACT_VERSION,
    },
    {
        "resource_type": "websocket_event", "name": "control",
        "description": "Pause, reprise ou demande de continuation.",
        "payload": {"event_id": "uuid", "event_type": "control", "action": {}},
        "produced_by": ["action_pause", "action_resume", "action_continue"],
        "effects": [], "contract_version": CONTRACT_VERSION,
    },
    {
        "resource_type": "websocket_event", "name": "retry",
        "description": "Tentative supplémentaire d'une action rejouable.",
        "payload": {"event_id": "uuid", "event_type": "retry", "action": {}},
        "produced_by": ["action executor"], "effects": [], "contract_version": CONTRACT_VERSION,
    },
    {
        "resource_type": "websocket_event", "name": "capture",
        "description": "État d'une capture liée à une action.",
        "payload": {"event_id": "uuid", "event_type": "capture", "action": {}},
        "produced_by": ["action executor", "capture subsystem"],
        "effects": [], "contract_version": CONTRACT_VERSION,
    },
    {
        "resource_type": "websocket_event", "name": "result",
        "description": "Annotation de résultat sans transition d'état.",
        "payload": {"event_id": "uuid", "event_type": "result", "action": {}},
        "produced_by": ["action registry"], "effects": [], "contract_version": CONTRACT_VERSION,
    },
]

for _event_contract in _EVENT_CONTRACTS:
    _event_contract.update({
        "category": "websocket_event",
        "parameters": {},
        "static_constraints": ["Connexion loopback authentifiée par bearer."],
        "dynamic_constraints": ["Le serveur d'événements et le moteur d'actions doivent être disponibles."],
        "examples": {"event": copy.deepcopy(_event_contract["payload"])},
        "errors": [],
        "events": [],
        "availability": {"status": "available", "requirement": "actions",
                         "version": CONTRACT_VERSION},
        "response": {"type": "websocket_event",
                     "example": copy.deepcopy(_event_contract["payload"])},
    })
    _add_event(_event_contract)


def command_contract(name: str) -> dict[str, Any] | None:
    """Return the private routing contract; callers must not mutate it."""
    return COMMAND_CONTRACTS.get(name)


def command_names() -> frozenset[str]:
    return frozenset(COMMAND_CONTRACTS)


def action_names() -> frozenset[str]:
    return frozenset(ACTION_CONTRACTS)


def _validate_value(name: str, value: Any, schema: dict[str, Any]) -> None:
    kind = schema["type"]
    valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string_or_integer": (isinstance(value, str) or
                              (isinstance(value, int) and not isinstance(value, bool))),
    }.get(kind, False)
    if not valid:
        raise ValueError(f"{name} must be of type {kind}")
    allowed = schema.get("allowed_values")
    if allowed is not None:
        if isinstance(value, list):
            if any(item not in allowed for item in value):
                raise ValueError(f"{name} contains an unsupported value")
        elif value not in allowed:
            raise ValueError(f"{name} has an unsupported value")
    limits = dict(schema.get("constraints", {}))
    for key in ("minimum", "minimum_exclusive", "maximum", "not", "min_length",
                "max_length", "min_items", "max_items", "unique_items"):
        if key in schema:
            limits[key] = schema[key]
    if "minimum" in limits and value < limits["minimum"]:
        raise ValueError(f"{name} is below its minimum")
    if "minimum_exclusive" in limits and value <= limits["minimum_exclusive"]:
        raise ValueError(f"{name} is below its exclusive minimum")
    if "maximum" in limits and value > limits["maximum"]:
        raise ValueError(f"{name} exceeds its maximum")
    if limits.get("not") == value:
        raise ValueError(f"{name} contains a forbidden value")
    if "min_length" in limits and len(value) < limits["min_length"]:
        raise ValueError(f"{name} is too short")
    if "max_length" in limits and len(value) > limits["max_length"]:
        raise ValueError(f"{name} is too long")
    if "min_items" in limits and len(value) < limits["min_items"]:
        raise ValueError(f"{name} has too few items")
    if "max_items" in limits and len(value) > limits["max_items"]:
        raise ValueError(f"{name} has too many items")
    if limits.get("unique_items") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
        raise ValueError(f"{name} contains duplicate items")
    if isinstance(value, dict):
        for child_name, child_schema in schema.get("properties", {}).items():
            if child_schema.get("required") and child_name not in value:
                raise ValueError(f"missing required parameter: {name}.{child_name}")
            if child_name in value:
                _validate_value(f"{name}.{child_name}", value[child_name], child_schema)


def validate_parameters(values: dict[str, Any], contract: dict[str, Any]) -> None:
    if not isinstance(values, dict):
        raise ValueError("arguments must be an object")
    for name, schema in contract["parameters"].items():
        if schema.get("required") and name not in values:
            raise ValueError(f"missing required parameter: {name}")
        if name in values:
            _validate_value(name, values[name], schema)


def validate_action_contract(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("action must be an object")
    kind = str(spec.get("kind", ""))
    contract = ACTION_CONTRACTS.get(kind)
    if contract is None:
        raise ValueError("unknown action kind")
    validate_parameters(spec, contract)
    return contract


def build_catalog(
    *,
    name: str | None = None,
    category: str | None = None,
    include: list[str] | None = None,
    availability: dict[str, bool] | None = None,
) -> dict[str, Any]:
    sections = include or ["commands", "action_types", "websocket_events"]
    allowed_sections = {"commands", "action_types", "websocket_events"}
    if not sections or any(section not in allowed_sections for section in sections):
        raise ValueError("invalid catalog section")
    if name is not None and name not in COMMAND_CONTRACTS:
        raise ValueError("unknown catalog command")
    categories = sorted({item["category"] for item in COMMAND_CONTRACTS.values()})
    if category is not None and category not in categories:
        raise ValueError("unknown catalog category")

    commands: list[dict[str, Any]] = []
    if "commands" in sections:
        for contract in COMMAND_CONTRACTS.values():
            if name is not None and contract["name"] != name:
                continue
            if category is not None and contract["category"] != category:
                continue
            public = copy.deepcopy(contract)
            public.pop("_handler", None)
            requirement = public["availability"].get("requirement")
            if requirement and availability is not None and not availability.get(requirement, False):
                public["availability"]["status"] = "unavailable"
            commands.append(public)

    action_types = ([copy.deepcopy(item) for item in ACTION_CONTRACTS.values()]
                    if "action_types" in sections else [])
    websocket_events = ([copy.deepcopy(item) for item in WEBSOCKET_EVENT_CONTRACTS.values()]
                        if "websocket_events" in sections else [])
    if availability is not None and not availability.get("actions", False):
        for item in action_types + websocket_events:
            item["availability"]["status"] = "unavailable"
    return {
        "contract_version": CONTRACT_VERSION,
        "endpoint": {"method": "POST", "path": API_PATH, "network": "loopback only",
                     "authentication": "Authorization: Bearer <token>",
                     "maximum_body_bytes": 8192},
        "envelope": {
            "required": ["command_id", "issued_at_ms", "ttl_ms", "command"],
            "command_id": {"type": "string", "max_length": 128, "unique_for_ttl": True},
            "issued_at_ms": {"type": "integer", "clock_skew_future_ms": 1000},
            "ttl_ms": {"type": "integer", "minimum": 1, "maximum": 5000},
            "arguments": {"type": "object", "default": {}},
            "rate_limit_per_second": 200,
        },
        "action_execution": {
            "states": {
                "ACCEPTED": "Action validée et placée dans la file.",
                "RUNNING": "Exécution commencée.",
                "EXECUTED": "Effet demandé émis, sans confirmation applicative implicite.",
                "CONFIRMED": "Effet confirmé par une observation indépendante.",
                "FAILED": "Échec établi avant effet non idempotent ambigu.",
                "UNKNOWN": "Un effet non idempotent a pu être émis; aucun rejeu automatique.",
                "CANCELLED": "Action annulée.",
            },
            "anti_replay": {
                "default_retention_seconds": 2_592_000,
                "runtime_value": "capabilities.action_id_retention_seconds",
                "expiry": "Après la rétention configurée et seulement lorsque l'état a été évincé.",
            },
        },
        "websocket": {
            "path": "/v1/events", "network": "loopback only",
            "authentication": "Authorization: Bearer <token>",
            "protocol": "mousse.actions.v1",
        },
        "categories": categories,
        "filters": {"name": name, "category": category, "include": list(sections)},
        "counts": {"commands": len(commands), "action_types": len(action_types),
                   "websocket_events": len(websocket_events)},
        "totals": {"commands": len(COMMAND_CONTRACTS), "action_types": len(ACTION_CONTRACTS),
                   "websocket_events": len(WEBSOCKET_EVENT_CONTRACTS)},
        **({"commands": commands} if "commands" in sections else {}),
        **({"action_types": action_types} if "action_types" in sections else {}),
        **({"websocket_events": websocket_events} if "websocket_events" in sections else {}),
    }


def validate_registry() -> None:
    """Fail fast if the declarative registry itself is malformed."""
    required = {"resource_type", "name", "description", "category", "parameters",
                "static_constraints", "dynamic_constraints", "examples", "errors", "effects",
                "events", "availability", "response", "contract_version"}
    if len(COMMAND_CONTRACTS) != len(set(COMMAND_CONTRACTS)):
        raise ValueError("duplicate command contract")
    for name, contract in COMMAND_CONTRACTS.items():
        if name != contract["name"] or not required.issubset(contract):
            raise ValueError(f"invalid command contract: {name}")
        if not contract.get("_handler"):
            raise ValueError(f"missing command handler: {name}")
        validate_parameters(contract["examples"]["request"].get("arguments", {}), contract)
    for name, contract in ACTION_CONTRACTS.items():
        if name != contract["name"] or not required.issubset(contract):
            raise ValueError(f"invalid action contract: {name}")
        validate_action_contract(contract["examples"]["request_fragment"])
    for name, contract in WEBSOCKET_EVENT_CONTRACTS.items():
        if name != contract["name"] or not required.issubset(contract):
            raise ValueError(f"invalid WebSocket event contract: {name}")


def render_markdown_reference() -> str:
    """Render the committed API reference from the live registry."""
    lines = [
        "# Référence API Mousse-controler",
        "",
        "<!-- Generated by scripts/generate_api_reference.py; do not edit manually. -->",
        "",
        f"Version du contrat : `{CONTRACT_VERSION}`.",
        "",
        "Toutes les commandes utilisent `POST /v1/command`, sur l'interface loopback, avec "
        "`Authorization: Bearer <token>`. L'enveloppe exige `command_id`, `issued_at_ms`, "
        "`ttl_ms` (1 à 5000 ms), `command` et accepte `arguments`.",
        "",
        "Les horodatages `issued_at_ms` présents dans les exemples sont purement illustratifs. "
        "Avant d'utiliser une requête, remplacer cette valeur par l'heure Unix actuelle en "
        "millisecondes ; une valeur d'exemple ancienne sera refusée par le contrôle de TTL.",
        "",
        f"Le registre contient **{len(COMMAND_CONTRACTS)} commandes**, "
        f"**{len(ACTION_CONTRACTS)} types d'actions** et "
        f"**{len(WEBSOCKET_EVENT_CONTRACTS)} événements WebSocket**.",
        "",
        "## Lecture des contraintes",
        "",
        "Les **contraintes statiques** sont validées automatiquement par le registre avant le "
        "routage : présence et type des paramètres, valeurs autorisées, bornes et structure "
        "déclarée. Une requête qui ne les respecte pas n'atteint pas le gestionnaire de commande.",
        "",
        "Les **contraintes dynamiques** dépendent de l'état réel au moment de l'exécution : "
        "disponibilité du transport ou d'un moteur, fraîcheur de la position, état d'une action "
        "ou d'une séquence, topologie et capacités HID. Le catalogue les décrit, mais elles sont "
        "vérifiées par les composants concernés (contrôleur, transport, moteurs d'actions et de "
        "séquences, ou gestionnaire de captures). Leur présence dans le catalogue ne garantit "
        "donc pas qu'elles soient satisfaites lors d'un appel ultérieur.",
        "",
        "## Commandes API",
        "",
    ]
    for contract in COMMAND_CONTRACTS.values():
        lines.extend([
            f"### `{contract['name']}`",
            "",
            f"{contract['description']} Catégorie : `{contract['category']}`. "
            f"Disponibilité : `{contract['availability']['status']}`.",
            "",
        ])
        if contract["parameters"]:
            lines.extend(["| Paramètre | Type | Obligatoire | Défaut | Contraintes |", "|---|---|---:|---|---|"])
            for name, schema in contract["parameters"].items():
                default = json.dumps(schema.get("default"), ensure_ascii=False) if "default" in schema else "—"
                constraints = []
                if "allowed_values" in schema:
                    constraints.append("valeurs=" + json.dumps(schema["allowed_values"], ensure_ascii=False))
                if schema.get("constraints"):
                    constraints.append(json.dumps(schema["constraints"], ensure_ascii=False, sort_keys=True))
                lines.append(
                    f"| `{name}` | `{schema['type']}` | {'oui' if schema['required'] else 'non'} | "
                    f"`{default}` | {'; '.join(constraints) or '—'} |"
                )
            lines.append("")
        if contract["dynamic_constraints"]:
            lines.append("Contraintes dynamiques : " + " ".join(contract["dynamic_constraints"]))
            lines.append("")
        lines.extend([
            "Exemple de requête :",
            "",
            "```json",
            json.dumps(contract["examples"]["request"], ensure_ascii=False, indent=2),
            "```",
            "",
            "Exemple de réponse :",
            "",
            "```json",
            json.dumps(contract["examples"]["response"], ensure_ascii=False, indent=2),
            "```",
            "",
            "Erreurs documentées : " + (", ".join(f"`{item}`" for item in contract["errors"]) or "aucune spécifique."),
            "",
            "Effets potentiels : " + (" ".join(contract["effects"]) or "aucun effet applicatif."),
            "",
        ])

    lines.extend(["## Types d'actions", "", "Une action est une ressource soumise par `action_submit`; ce n'est pas une commande API.", ""])
    for contract in ACTION_CONTRACTS.values():
        required = [name for name, schema in contract["parameters"].items() if schema.get("required")]
        lines.extend([
            f"### `{contract['name']}`",
            "",
            contract["description"],
            "",
            "Paramètres obligatoires : " + ", ".join(f"`{item}`" for item in required) + ".",
            "",
        ])
        lines.extend(["| Paramètre | Type | Obligatoire | Défaut | Valeurs/contraintes |", "|---|---|---:|---|---|"])
        for name, schema in contract["parameters"].items():
            default = json.dumps(schema.get("default"), ensure_ascii=False) if "default" in schema else "—"
            details = []
            if "allowed_values" in schema:
                details.append("valeurs=" + json.dumps(schema["allowed_values"], ensure_ascii=False))
            if schema.get("constraints"):
                details.append(json.dumps(schema["constraints"], ensure_ascii=False, sort_keys=True))
            if schema.get("conditional_default"):
                details.append("défaut conditionnel=" + json.dumps(
                    schema["conditional_default"], ensure_ascii=False, sort_keys=True))
            lines.append(
                f"| `{name}` | `{schema['type']}` | {'oui' if schema['required'] else 'non'} | "
                f"`{default}` | {'; '.join(details) or '—'} |"
            )
        lines.extend([
            "",
            "Exemple : `" + json.dumps(contract["examples"]["request_fragment"], ensure_ascii=False) + "`",
            "",
            "Contraintes dynamiques : " + (" ".join(contract["dynamic_constraints"]) or "aucune spécifique."),
            "",
            "Effets potentiels : " + " ".join(contract["effects"]),
            "",
        ])

    lines.extend([
        "## États d'exécution",
        "",
        "`ACCEPTED`, `RUNNING`, `EXECUTED`, `CONFIRMED`, `FAILED`, `UNKNOWN` et `CANCELLED`. "
        "Un effet HID non confirmable peut finir à `EXECUTED`; un échec après émission non idempotente "
        "finit à `UNKNOWN` afin d'interdire un rejeu automatique ambigu.",
        "",
        "## Événements WebSocket",
        "",
        "Le serveur WebSocket authentifié utilise le protocole `mousse.actions.v1`.",
        "",
        "| Événement | Description | Producteurs |",
        "|---|---|---|",
    ])
    for contract in WEBSOCKET_EVENT_CONTRACTS.values():
        lines.append(f"| `{contract['name']}` | {contract['description']} | {', '.join(contract['produced_by'])} |")
    lines.append("")
    return "\n".join(lines)


validate_registry()
