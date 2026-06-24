from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from .hypergraph import HypergraphEdge, HypergraphNode, HypergraphRecord


DEFAULT_KERNEL_ORDER = (
    "source",
    "focal_load",
    "preflight_anchor",
    "honesty",
    "security",
    "boundary",
    "identity_scope",
    "faculty_fields",
    "pattern_collection",
    "packet_compile",
    "inference_run",
    "trace",
)

DEFAULT_SELECTED_PATTERNS = (
    "SecurityHonestyGovernance",
    "BoundaryFacultyInspection",
    "LocalIdentityConsumption",
    "FacultyAttentionFieldNaming",
    "AttentionBalanceCenter",
)


@dataclass(frozen=True)
class FacultyFieldSignature:
    attention_system: str
    field_noun: str
    boundary_noun: str
    residual_noun: str
    feature_account: str

    @property
    def signature(self) -> str:
        return "::".join((self.attention_system, self.field_noun, self.boundary_noun, self.residual_noun))

    @property
    def compact_notation(self) -> str:
        return f"({self.attention_system}) :{self.field_noun}: /{self.boundary_noun}/ |{self.residual_noun}|"

    def scoped_identifier(self, node_scope: str = "F_sop") -> str:
        return "::".join(
            (
                _safe_key(node_scope),
                "FacultyAttentionFieldNaming",
                _safe_key(self.attention_system),
                _safe_key(self.field_noun),
                _safe_key(self.signature),
            )
        )


@dataclass(frozen=True)
class ReflectionConsumption:
    reflection_artifact: str
    origin_system: str
    consumer_system: str
    consumption_mode: str = "compiled"
    consumption_proof: str = "runtime_invocation"
    local_status: str = "local_consumption"

    @property
    def ledger_key(self) -> str:
        return _safe_key(f"{self.consumer_system}_{self.reflection_artifact}_{self.consumption_mode}")


@dataclass(frozen=True)
class CompiledAttentionKernel:
    packet_id: str
    focus_subject: str
    job_need: str
    selected_patterns: tuple[str, ...]
    faculty_fields: tuple[FacultyFieldSignature, ...]
    reflection_consumptions: tuple[ReflectionConsumption, ...]
    impulse: str
    balance_score: str
    balance_alerts: tuple[str, ...]
    namespace_collisions: tuple[str, ...]
    focus_terms: tuple[str, ...] = field(default_factory=tuple)
    periphery_terms: tuple[str, ...] = field(default_factory=tuple)
    model_lane: str = "default"
    output_target: str = "sop"
    depth: str = "normal"
    trace_target: str = "events/periphery_stream"
    residual_outside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return bool(self.packet_id and self.focus_subject and self.job_need and self.selected_patterns)

    @property
    def kernel_order(self) -> tuple[str, ...]:
        return DEFAULT_KERNEL_ORDER

    @property
    def namespace_identifiers(self) -> tuple[str, ...]:
        pattern_identifiers = tuple(
            "::".join(("F_sop", "AttentionKernelCompiler", _safe_key(pattern), "pattern", _safe_key(pattern)))
            for pattern in self.selected_patterns
        )
        field_identifiers = tuple(field.scoped_identifier() for field in self.faculty_fields)
        return pattern_identifiers + field_identifiers

    def render(self) -> str:
        lines = [
            "Subject: Compiled Attention Kernel Packet",
            "",
            f"& [CompiledAttentionKernel:{_safe_key(self.packet_id)}] is an in-context attention packet",
            f"  + [packet_id] is {self.packet_id}",
            f"  + [focus_subject] is {self.focus_subject}",
            f"  + [job_need] is {self.job_need}",
            f"  + [model_lane] is {self.model_lane}",
            f"  + [output_target] is {self.output_target}",
            f"  + [depth] is {self.depth}",
            f"  + [kernel_order] is {', '.join(self.kernel_order)}",
            f"  + [selected_patterns] is {', '.join(self.selected_patterns)}",
            f"  + [impulse] is {self.impulse or 'not_supplied'}",
            f"  + [balance_score] is {self.balance_score}",
            f"  + [balance_alerts] is {', '.join(self.balance_alerts) if self.balance_alerts else 'none'}",
            f"  + [namespace_collisions] is {', '.join(self.namespace_collisions) if self.namespace_collisions else 'none'}",
            f"  + [trace_target] is {self.trace_target}",
            "",
            "& [KernelPreflight] is the first-layer order",
            "  + [security_honesty_kernel] is first",
            "  + [boundary_inspection_preflight] is after Security/Honesty when boundaries are load-bearing",
            "  + [identity_scope_preflight] is before pattern collection when identity or shared naming is load-bearing",
            "  + [faculty_field_preflight] is before packet emission when custom faculty field names are load-bearing",
            "",
            "& [FacultyFieldSignatureSet] is scoped feature-account field naming",
        ]
        for index, field_signature in enumerate(self.faculty_fields, start=1):
            lines.extend(
                (
                    f"  + [faculty_field_{index:03d}] is {field_signature.compact_notation}",
                    f"    = scoped_identifier: {field_signature.scoped_identifier()}",
                    f"    = feature_account: {field_signature.feature_account}",
                )
            )
        lines.append("")
        lines.append("& [ReflectionConsumptionLedger] is per-consumer proof for imported or compiled reflections")
        for index, consumption in enumerate(self.reflection_consumptions, start=1):
            lines.extend(
                (
                    f"  + [consumption_{index:03d}] is {consumption.reflection_artifact}",
                    f"    = origin_system: {consumption.origin_system}",
                    f"    = consumer_system: {consumption.consumer_system}",
                    f"    = consumption_mode: {consumption.consumption_mode}",
                    f"    = consumption_proof: {consumption.consumption_proof}",
                    f"    = local_status: {consumption.local_status}",
                )
            )
        lines.extend(
            (
                "",
                "(compiled_attention_kernel) :focus_subject: /kernel_preflight/ |outside|",
                f"  = focus_subject: {self.focus_subject}",
                f"  = job_need: {self.job_need}",
                f"  = balance_score: {self.balance_score}",
                f"  = impulse: {self.impulse or 'not_supplied'}",
                "  - outside: hidden model internals, literal antivirus guarantees, semantic proof, and unverified inference effects",
            )
        )
        for item in self.residual_outside:
            lines.append(f"  - outside: {item}")
        return "\n".join(lines)

    def to_hypergraph(self) -> HypergraphRecord:
        graph_id = _safe_key(self.packet_id)
        compiler_node = HypergraphNode(
            f"N:compiler:{graph_id}",
            "attention kernel runtime compiler",
            (("packet_id", self.packet_id), ("balance_score", self.balance_score)),
        )
        packet_node = HypergraphNode(f"N:source:{graph_id}_packet", "compiled attention kernel packet")
        focus_node = HypergraphNode(f"N:focus:{_safe_key(self.focus_subject)}", self.focus_subject)
        governor_node = HypergraphNode("N:governor:security_honesty_kernel", "Security/Honesty first-layer kernel")
        honesty_node = HypergraphNode("N:honesty:honesty_kernel_operator", "Honesty truth operator")
        security_node = HypergraphNode("N:security:security_kernel_operator", "Security safety operator")
        boundary_node = HypergraphNode("N:boundary:boundary_inspection_preflight", "boundary inspection preflight")
        namespace_node = HypergraphNode("N:namespace:attention_kernel_namespace", "compiled packet namespace")
        ledger_node = HypergraphNode("N:ledger:reflection_consumption_ledger", "reflection consumption ledger")
        balance_node = HypergraphNode(
            f"N:balance:{graph_id}",
            "attention kernel balance",
            (("balance_score", self.balance_score), ("alerts", ",".join(self.balance_alerts) or "none")),
        )
        impulse_node = HypergraphNode(
            f"N:signal:{graph_id}_impulse",
            self.impulse or "impulse not supplied",
            (("signal_role", "impulse"),),
        )
        outside_node = HypergraphNode("N:outside:attention_kernel_runtime_boundary", "hidden model state and unverified effects")
        nodes: list[HypergraphNode] = [
            compiler_node,
            packet_node,
            focus_node,
            governor_node,
            honesty_node,
            security_node,
            boundary_node,
            namespace_node,
            ledger_node,
            balance_node,
            impulse_node,
            outside_node,
        ]
        edges: list[HypergraphEdge] = [
            HypergraphEdge(
                f"E:compiles:{graph_id}",
                "compiles",
                (("compiler", compiler_node.key), ("packet", packet_node.key), ("focus", focus_node.key)),
            ),
            HypergraphEdge(
                f"E:preflights:{graph_id}",
                "preflights",
                (
                    ("governor", governor_node.key),
                    ("honesty", honesty_node.key),
                    ("security", security_node.key),
                    ("boundary", boundary_node.key),
                ),
            ),
            HypergraphEdge(
                f"E:orders:{graph_id}",
                "orders",
                (("compiler", compiler_node.key), ("governor", governor_node.key), ("namespace", namespace_node.key)),
                (("kernel_order", ",".join(self.kernel_order)),),
            ),
            HypergraphEdge(
                f"E:scopes:{graph_id}",
                "scopes",
                (("namespace", namespace_node.key), ("packet", packet_node.key)),
                (("identifier_count", str(len(self.namespace_identifiers))),),
            ),
            HypergraphEdge(
                f"E:alerts:{graph_id}_balance",
                "alerts",
                (("balance", balance_node.key), ("signal", impulse_node.key), ("outside", outside_node.key)),
                (("balance_score", self.balance_score),),
            ),
            HypergraphEdge(
                f"E:bounds:{graph_id}",
                "bounds",
                (("compiler", compiler_node.key), ("outside", outside_node.key)),
            ),
        ]
        for index, pattern in enumerate(self.selected_patterns, start=1):
            scaffold_node = HypergraphNode(f"N:scaffold:{_safe_key(pattern)}", pattern)
            nodes.append(scaffold_node)
            edges.append(
                HypergraphEdge(
                    f"E:loads:{graph_id}_{index:03d}",
                    "loads",
                    (("compiler", compiler_node.key), ("scaffold", scaffold_node.key), ("packet", packet_node.key)),
                )
            )
        for index, field_signature in enumerate(self.faculty_fields, start=1):
            field_key = f"N:field:{_safe_key(field_signature.signature)}"
            feature_key = f"N:term:{_safe_key(field_signature.feature_account)}"
            nodes.append(
                HypergraphNode(
                    field_key,
                    field_signature.compact_notation,
                    (("scoped_identifier", field_signature.scoped_identifier()),),
                )
            )
            nodes.append(HypergraphNode(feature_key, field_signature.feature_account))
            edges.append(
                HypergraphEdge(
                    f"E:names:{graph_id}_{index:03d}",
                    "names",
                    (("namespace", namespace_node.key), ("field", field_key)),
                )
            )
            edges.append(
                HypergraphEdge(
                    f"E:accounts_for:{graph_id}_{index:03d}",
                    "accounts_for",
                    (("field", field_key), ("feature", feature_key)),
                )
            )
        for index, consumption in enumerate(self.reflection_consumptions, start=1):
            reflection_node = HypergraphNode(
                f"N:reflection:{_safe_key(consumption.reflection_artifact)}",
                consumption.reflection_artifact,
            )
            origin_node = HypergraphNode(f"N:identity:{_safe_key(consumption.origin_system)}", consumption.origin_system)
            consumer_node = HypergraphNode(f"N:identity:{_safe_key(consumption.consumer_system)}", consumption.consumer_system)
            nodes.extend((reflection_node, origin_node, consumer_node))
            edges.append(
                HypergraphEdge(
                    f"E:consumes:{graph_id}_{index:03d}",
                    "consumes",
                    (
                        ("ledger", ledger_node.key),
                        ("reflection", reflection_node.key),
                        ("origin", origin_node.key),
                        ("consumer", consumer_node.key),
                    ),
                    (
                        ("mode", consumption.consumption_mode),
                        ("proof", consumption.consumption_proof),
                        ("local_status", consumption.local_status),
                    ),
                )
            )
        for index, collision in enumerate(self.namespace_collisions, start=1):
            collision_node = HypergraphNode(f"N:signal:{_safe_key(collision)}", collision)
            nodes.append(collision_node)
            edges.append(
                HypergraphEdge(
                    f"E:disambiguates:{graph_id}_{index:03d}",
                    "disambiguates",
                    (("namespace", namespace_node.key), ("signal", collision_node.key), ("outside", outside_node.key)),
                )
            )
        return HypergraphRecord(
            graph_id=graph_id,
            label=f"{self.packet_id} Attention Kernel",
            nodes=tuple(_dedupe_nodes(nodes)),
            edges=tuple(edges),
            attributes=(
                ("format_profile", "SOP-HG attention-kernel-runtime"),
                ("focus_subject", self.focus_subject),
                ("job_need", self.job_need),
            ),
            outside=self.residual_outside or ("compiled packet shapes in-context inference but does not alter hidden model state",),
        )


def build_attention_kernel_packet(
    *,
    packet_id: str,
    focus_subject: str,
    job_need: str,
    selected_patterns: Iterable[str] = (),
    faculty_fields: Iterable[FacultyFieldSignature] = (),
    reflection_consumptions: Iterable[ReflectionConsumption] = (),
    impulse: str = "",
    focus_terms: Iterable[str] = (),
    periphery_terms: Iterable[str] = (),
    model_lane: str = "default",
    output_target: str = "sop",
    depth: str = "normal",
    trace_target: str = "events/periphery_stream",
) -> CompiledAttentionKernel:
    patterns = tuple(pattern.strip() for pattern in selected_patterns if pattern.strip()) or DEFAULT_SELECTED_PATTERNS
    fields = tuple(faculty_fields) or default_faculty_fields()
    consumptions = tuple(reflection_consumptions) or (
        ReflectionConsumption(
            reflection_artifact="attention_kernel_runtime_invocation",
            origin_system="F_sop",
            consumer_system="F_sop",
            consumption_proof="local_runtime_builder",
        ),
    )
    normalized_focus_terms = tuple(_normalize(term) for term in focus_terms if _normalize(term))
    normalized_periphery_terms = tuple(_normalize(term) for term in periphery_terms if _normalize(term))
    namespace_collisions = _namespace_collisions(patterns, fields)
    balance_score, balance_alerts = _assess_balance(
        patterns=patterns,
        fields=fields,
        namespace_collisions=namespace_collisions,
        impulse=impulse,
        periphery_terms=normalized_periphery_terms,
    )
    return CompiledAttentionKernel(
        packet_id=packet_id,
        focus_subject=focus_subject,
        job_need=job_need,
        selected_patterns=patterns,
        faculty_fields=fields,
        reflection_consumptions=consumptions,
        impulse=impulse,
        balance_score=balance_score,
        balance_alerts=balance_alerts,
        namespace_collisions=namespace_collisions,
        focus_terms=normalized_focus_terms,
        periphery_terms=normalized_periphery_terms,
        model_lane=model_lane,
        output_target=output_target,
        depth=depth,
        trace_target=trace_target,
        residual_outside=("runtime packet is a visible prompt/control artifact, not proof of hidden attention mechanics",),
    )


def default_faculty_fields() -> tuple[FacultyFieldSignature, ...]:
    return (
        FacultyFieldSignature(
            "honesty_faculty",
            "claim",
            "distinction",
            "uncertainty",
            "truth status, support separation, contradiction, and fair representation",
        ),
        FacultyFieldSignature(
            "security_faculty",
            "assignment",
            "safe_boundary_line",
            "risk",
            "action assignment, permission, protected work, and safe operation",
        ),
    )


def parse_faculty_field(value: str) -> FacultyFieldSignature:
    parts = [part.strip() for part in value.split(":", 4)]
    if len(parts) != 5 or not all(parts[:4]):
        raise ValueError("faculty field must be system:field:boundary:residual:feature_account")
    return FacultyFieldSignature(*parts)


def parse_reflection_consumption(value: str) -> ReflectionConsumption:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 3:
        raise ValueError("reflection consumption must be artifact|origin|consumer[|proof|mode|local_status]")
    artifact, origin, consumer = parts[:3]
    proof = parts[3] if len(parts) > 3 and parts[3] else "runtime_invocation"
    mode = parts[4] if len(parts) > 4 and parts[4] else "compiled"
    local_status = parts[5] if len(parts) > 5 and parts[5] else "local_consumption"
    return ReflectionConsumption(
        reflection_artifact=artifact,
        origin_system=origin,
        consumer_system=consumer,
        consumption_proof=proof,
        consumption_mode=mode,
        local_status=local_status,
    )


def _namespace_collisions(patterns: tuple[str, ...], fields: tuple[FacultyFieldSignature, ...]) -> tuple[str, ...]:
    labels = [_normalize(pattern) for pattern in patterns]
    labels.extend(_normalize(field.field_noun) for field in fields)
    labels.extend(_normalize(field.boundary_noun) for field in fields)
    counts = Counter(label for label in labels if label)
    return tuple(sorted(label for label, count in counts.items() if count > 1))


def _assess_balance(
    *,
    patterns: tuple[str, ...],
    fields: tuple[FacultyFieldSignature, ...],
    namespace_collisions: tuple[str, ...],
    impulse: str,
    periphery_terms: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    alerts: list[str] = []
    if namespace_collisions:
        alerts.append("namespace_collision")
    if not impulse.strip():
        alerts.append("missing_impulse")
    if not periphery_terms:
        alerts.append("periphery_frame_thinning")
    if len(patterns) > 12:
        alerts.append("packet_pattern_overload")
    if not fields:
        alerts.append("missing_faculty_fields")

    if "packet_pattern_overload" in alerts:
        score = "overloaded"
    elif namespace_collisions:
        score = "wobbling"
    elif len(alerts) >= 2:
        score = "reduced"
    elif alerts:
        score = "watch"
    else:
        score = "stable"
    return score, tuple(alerts)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "node"


def _dedupe_nodes(nodes: list[HypergraphNode]) -> tuple[HypergraphNode, ...]:
    by_key: dict[str, HypergraphNode] = {}
    for node in nodes:
        by_key.setdefault(node.key, node)
    return tuple(by_key.values())
