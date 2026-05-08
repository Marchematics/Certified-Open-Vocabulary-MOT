from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class BaselineSpec:
    name: str
    detector: str
    tracker: str
    status: str
    note: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


DEFAULT_BASELINES = (
    BaselineSpec(
        name="GroundingDINO+ByteTrack",
        detector="GroundingDINO",
        tracker="ByteTrack",
        status="planned",
        note="Composable open-vocabulary detector plus MOT associator.",
    ),
    BaselineSpec(
        name="GroundingDINO+OC-SORT",
        detector="GroundingDINO",
        tracker="OC-SORT",
        status="planned",
        note="Composable detector plus motion-aware online tracker.",
    ),
    BaselineSpec(
        name="OVTrack",
        detector="OVTrack",
        tracker="OVTrack",
        status="planned",
        note="Native OVMOT backbone adapter placeholder.",
    ),
)
