"""
Sample data model for the D2 dashboard channels.
"""
import dataclasses
import datetime
import typing

Quality = typing.Literal['measured', 'imputed', 'forecast']

@dataclasses.dataclass(frozen=True)
class Sample:
    """A single time series sample."""
    timestamp: datetime.datetime  # timezone-aware, UTC
    value: float
    quality: Quality = 'measured'

    @staticmethod
    def to_dict(sample: 'Sample', convert_timestamp: bool = False, include_quality: bool = True) -> dict:
        """Convert the sample to a dictionary."""
        if include_quality:
            return {
                'timestamp': sample.timestamp.isoformat() if convert_timestamp else sample.timestamp,
                'value': sample.value,
                'quality': sample.quality,
            }
        else:
            return {
                'timestamp': sample.timestamp.isoformat() if convert_timestamp else sample.timestamp,
                'value': sample.value,
            }
