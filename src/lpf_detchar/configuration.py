import pydantic

from typing import Any, Optional


class OmicronConfiguration(pydantic.BaseModel):
    start_time: int
    """The starting time for the segment being analyzed, in seconds"""
    duration: int
    """The duration of the segment being analyzed, in seconds"""
    starting_sampling_frequency: float
    """The frequency at which the time series data is sampled, in Hz"""
    target_sampling_frequency: float
    """The sampling frequency to resample the time series data to, in Hz"""
    minimum_quality_factor: float
    """The minimum quality factor for the omicron tiles"""
    maximum_quality_factor: float
    """The maximum quality factor for the omicron tiles"""
    minimum_characteristic_frequency: Optional[float] = pydantic.Field(default=None)
    """The minimum characteristic frequency for the omicron tiles,
    defaults to 1 / duration"""
    maximum_characteristic_frequency: Optional[float] = pydantic.Field(default=None)
    """The maximum characteristic frequency for the omicron tiles,
    defaults to sampling_frequency / 2"""
    maximum_energy_loss: float
    """The maximum energy loss to allow when creating the omicron tiles"""
    snr_threshold: float
    """The SNR threshold to apply to each tile"""
    cluster_distance_threshold: float
    """The threshold to apply when generating the clusters, see the
    documentation for the eps argument in sklearn.cluster.DBSCAN"""
    maximum_triggers_per_segment: int
    """The maximum numbers of triggers to cluster in each segment, in order
    to avoid out-of-memory crashes when clustering"""
    minimum_frequency: Optional[float] = pydantic.Field(default=None)
    """The minimum frequency to analyze in the segment, separate from the 
    minimum tile frequency to generate (see `minimum_characteristic_frequency`)"""
    maximum_frequency: Optional[float] = pydantic.Field(default=None)
    """The maximum frequency to analyze in the segment, separate from the 
    maximum tile frequency to generate (see `minimum_characteristic_frequency`)"""
    tukey_alpha: float = pydantic.Field(default=0.2)
    """The alpha parameter for the tukey window applied before whitening the data"""
    number_welch_segments: int = pydantic.Field(default=16)
    """The number of segments to use when Welch's method to compute the PSD of the data"""

    @pydantic.model_validator(mode="before")
    @classmethod
    def set_minimum_characteristic_frequency_default(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return
        duration = values.get("duration", None)
        if (
            isinstance(duration, int)
            and values.get("minimum_characteristic_frequency") is None
        ):
            values["minimum_characteristic_frequency"] = 2 / duration
        return values

    @pydantic.model_validator(mode="before")
    @classmethod
    def set_maximum_characteristic_frequency_default(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return
        target_sampling_frequency = values.get("target_sampling_frequency", None)
        if target_sampling_frequency is None:
            return
        else:
            target_sampling_frequency = float(target_sampling_frequency)
        if (
            isinstance(target_sampling_frequency, float)
            and values.get("maximum_characteristic_frequency") is None
        ):
            values["maximum_characteristic_frequency"] = target_sampling_frequency / 2
        return values
