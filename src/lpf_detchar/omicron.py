import jax
import jax.numpy as jnp
from dbscan import JaxDBScan
from scipy.signal import welch, get_window, detrend

from jax.typing import ArrayLike
from typing import Callable, Optional

from .configuration import OmicronConfiguration
from .logging import logger


def resample_timeseries(
    time_domain_data: jnp.ndarray,
    starting_sampling_frequency: float,
    target_sampling_frequency: float,
    duration: float,
):
    segment_times = jnp.linspace(
        0,
        duration - 1 / starting_sampling_frequency,
        int(duration * starting_sampling_frequency),
    )
    target_times = jnp.linspace(
        0,
        duration - 1 / target_sampling_frequency,
        int(duration * target_sampling_frequency),
    )
    time_domain_data_resampled = jnp.interp(
        target_times, segment_times, time_domain_data
    )
    return time_domain_data_resampled


def whiten_timeseries(
    time_domain_data,
    sampling_frequency,
    duration,
    tukey_alpha=0.2,
    number_welch_segments=16,
    minimum_frequency=None,
    maximum_frequency=None,
):
    # if minimum_frequency is not None and maximum_frequency is not None:
    #     minimum_frequency_index = 2 * minimum_frequency / sampling_frequency
    #     maximum_frequency_index = 2 * maximum_frequency / sampling_frequency
    #     b, a = butter(10, (minimum_frequency_index, maximum_frequency_index), btype="bandpass")
    #     time_domain_data = filtfilt(b, a, time_domain_data)
    # elif minimum_frequency is not None:
    #     minimum_frequency_index = 2 * minimum_frequency / sampling_frequency
    #     b, a = butter(10, minimum_frequency_index, btype="highpass")
    #     time_domain_data = filtfilt(b, a, time_domain_data)
    # elif maximum_frequency is not None:
    #     maximum_frequency_index = 2 * maximum_frequency / sampling_frequency
    #     b, a = butter(10, maximum_frequency_index, btype="lowpass")
    #     time_domain_data = filtfilt(b, a, time_domain_data)

    tukey_window = get_window(("tukey", tukey_alpha), len(time_domain_data))

    windowed_time_domain_data = detrend(time_domain_data) * tukey_window
    # windowed_time_domain_data = time_domain_data * tukey_window
    window_factor = jnp.mean(tukey_window**2)
    window_scale = jnp.sqrt(window_factor)

    number_samples = len(windowed_time_domain_data)
    frequencies = jnp.linspace(0, sampling_frequency / 2, number_samples // 2 + 1)
    frequency_domain_data = jnp.fft.rfft(windowed_time_domain_data) / sampling_frequency

    psd_frequencies, psd = welch(
        time_domain_data,
        fs=sampling_frequency,
        average="mean",
        window=("tukey", tukey_alpha),
        nperseg=int(sampling_frequency * duration / number_welch_segments),
        noverlap=0,
    )
    interpolated_psd = jnp.interp(frequencies, psd_frequencies, psd)

    if minimum_frequency is not None and maximum_frequency is not None:
        frequency_mask = (frequencies > minimum_frequency) & (
            frequencies < maximum_frequency
        )
    elif minimum_frequency is not None:
        frequency_mask = frequencies > minimum_frequency
    elif maximum_frequency is not None:
        frequency_mask = frequencies < maximum_frequency
    else:
        frequency_mask = jnp.ones(frequencies.shape).astype(bool)
    mask_factor = jnp.mean(frequency_mask)

    frequency_domain_data_whitened = (
        frequency_domain_data
        * frequency_mask
        / (0.5 * jnp.sqrt(duration))
        / jnp.sqrt(interpolated_psd)
        / window_scale
    )

    time_domain_data_whitened = (
        jnp.fft.irfft(frequency_domain_data_whitened)
        * jnp.sum(frequency_mask) ** 0.5
        / mask_factor
    )
    return (
        time_domain_data_whitened,
        frequency_domain_data_whitened,
        frequency_mask,
        interpolated_psd,
    )


def get_tiles(
    energy_loss_max,
    quality_factor_max,
    quality_factor_min,
    characteristic_frequency_max,
    characteristic_frequency_min,
    time_max,
    time_min,
    max_number_time_samples,
) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    quality_factor_metric_distance = jnp.log(
        quality_factor_max / quality_factor_min
    ) / jnp.sqrt(2)
    number_quality_factor_values = jnp.ceil(
        quality_factor_metric_distance / 2 / jnp.sqrt(energy_loss_max / 3)
    )

    characteristic_frequency_metric_distance = (
        jnp.sqrt(quality_factor_max**2 + 2)
        * jnp.log(characteristic_frequency_max / characteristic_frequency_min)
        / 2
    )
    number_characteristic_frequency_values = jnp.ceil(
        characteristic_frequency_metric_distance / 2 / jnp.sqrt(energy_loss_max / 3)
    )

    time_metric_distance = (
        2
        * jnp.pi
        * characteristic_frequency_max
        * (time_max - time_min)
        / quality_factor_min
    )
    number_time_values = jnp.minimum(
        jnp.ceil(time_metric_distance / 2 / jnp.sqrt(energy_loss_max / 3)),
        max_number_time_samples,
    )

    quality_factors = quality_factor_min * (
        quality_factor_max / quality_factor_min
    ) ** (
        (0.5 + jnp.arange(number_quality_factor_values)) / number_quality_factor_values
    )
    characteristic_frequencies = characteristic_frequency_min * (
        characteristic_frequency_max / characteristic_frequency_min
    ) ** (
        (0.5 + jnp.arange(number_characteristic_frequency_values))
        / number_characteristic_frequency_values
    )
    times = (
        time_min
        + (jnp.arange(number_time_values) + 0.5)
        * (time_max - time_min)
        / number_time_values
    )

    return quality_factors, characteristic_frequencies, times


@jax.jit
def frequency_domain_omicron_windows(
    frequency_array: jnp.ndarray,
    characteristic_frequencies: jnp.ndarray,
    quality_factors: jnp.ndarray,
) -> jnp.ndarray:
    """The Omicron bi-square windows for a set of characteristic frequencies and quality factors

    Parameters
    ==========
        frequency_array : jnp.ndarray
            The array of frequencies over which to compute the window. Shape (M,)
        characteristic_frequencies : jnp.ndarray
            The characteristic frequencies of the windows ($\\phi$ in Robinet). Shape (N,)
        quality_factor : jnp.ndarray
            The quality factors for the windows. Shape (O,)

    Returns
    =======
        windows : jnp.ndarray
            Shape (M, N, O)
    """
    # Robinet technical document equations 8-13
    # Note shift to characteristic frequency here instead of shifting data
    # Dimensions len(frequency_array) x len(characteristic_frequencies) x len(quality_factors)

    # Shape (N, O)
    window_halfwidths = (
        jnp.sqrt(11) * characteristic_frequencies[:, None] / quality_factors[None, :]
    )
    # Shape (N, O)
    normalization_factors = jnp.sqrt(2 * 315 / 128 / window_halfwidths)
    # Shape (M, N, O)
    kernels = (
        normalization_factors[None, :, :]
        * (
            1
            - (
                (
                    frequency_array[:, None, None]
                    - characteristic_frequencies[None, :, None]
                )
                / window_halfwidths[None, :, :]
            )
            ** 2
        )
        ** 2
    )
    # Shape (M, N, O)
    windows = jnp.where(
        jnp.abs(
            frequency_array[:, None, None] - characteristic_frequencies[None, :, None]
        )
        < window_halfwidths[None, :, :],
        kernels,
        0,
    )
    return windows

@jax.jit
def get_energy_in_tiles_time_domain_data(
    time_domain_data: jnp.ndarray,
    frequency_mask: jnp.ndarray,
    times: jnp.ndarray,
    characteristic_frequencies: jnp.ndarray,
    quality_factors: jnp.ndarray,
    sampling_frequency: int,
) -> jnp.ndarray:
    """Gets the energy in an array of omicron tiles

    Parameters
    ==========
        time_domain_data : jnp.ndarray
            The array of time domain data being analyzed, of shape (M,)
        times : jnp.ndarray
            The array of central times of the omicron tiles, of shape (P,)
        characteristic_frequencies : jnp.ndarray
            The array of characteristic frequencies of the tiles ($\\phi$ in Robinet). Shape (N,)
        quality_factor : jnp.ndarray
            The array of quality factors for the tiles. Shape (O,)
        sampling_frequency : int
            The sampling frequency for the data

    Returns
    =======
        jnp.ndarray
            The energy in each tile, of shape (P, N, O)
    """
    # Frequencies are shape (M/2+1,), hereafter (M',)
    # Characteristic frequencies are shape (N,)
    # Quality factors are shape (O,)
    # Time tiles are shape (P,)
    frequency_array = jnp.linspace(
        0, sampling_frequency / 2, len(time_domain_data) // 2 + 1
    )
    duration = 1 / (frequency_array[1] - frequency_array[0])
    frequency_domain_data = (
        jnp.fft.rfft(time_domain_data)
        / sampling_frequency
        / jnp.sqrt(duration)
    )
    # Shape M', N, O
    windows = frequency_domain_omicron_windows(
        frequency_array=frequency_array,
        characteristic_frequencies=characteristic_frequencies,
        quality_factors=quality_factors,
    )
    # Shape M', N
    frequency_minus_characteristic_frequency_tiles = (
        frequency_array[:, None] - characteristic_frequencies[None, :]
    )
    # Shape M', N, O
    frequency_domain_data_windowed = frequency_domain_data[:, None, None] * windows
    # Shape P, M', N
    time_shift_tiles = jnp.exp(
        1j
        * 2
        * jnp.pi
        * frequency_minus_characteristic_frequency_tiles[None, :, :]
        * times[:, None, None]
    )
    # Shape P, N, O
    tile_timeseries = (
        jnp.sum(
            frequency_domain_data_windowed[None, :, :, :]
            * time_shift_tiles[:, :, :, None],
            axis=1,
        )
        / duration
    )
    return jnp.abs(tile_timeseries) ** 2


@jax.jit
def get_energy_in_tiles_frequency_domain_data(
    frequency_domain_data: jnp.ndarray,
    frequency_mask: jnp.ndarray,
    times: jnp.ndarray,
    characteristic_frequencies: jnp.ndarray,
    quality_factors: jnp.ndarray,
    sampling_frequency: int,
) -> jnp.ndarray:
    """Gets the energy in an array of omicron tiles

    Parameters
    ==========
        frequency_domain_data : jnp.ndarray
            The array of time domain data being analyzed, of shape (M,)
        times : jnp.ndarray
            The array of central times of the omicron tiles, of shape (P,)
        characteristic_frequencies : jnp.ndarray
            The array of characteristic frequencies of the tiles ($\\phi$ in Robinet). Shape (N,)
        quality_factor : jnp.ndarray
            The array of quality factors for the tiles. Shape (O,)
        sampling_frequency : int
            The sampling frequency for the data

    Returns
    =======
        jnp.ndarray
            The energy in each tile, of shape (P, N, O)
    """
    # Frequencies are shape (M,)
    # Characteristic frequencies are shape (N,)
    # Quality factors are shape (O,)
    # Time tiles are shape (P,)
    frequency_array = jnp.linspace(
        0, sampling_frequency / 2, len(frequency_domain_data)
    )
    duration = 1 / (frequency_array[1] - frequency_array[0])
    frequency_domain_data = frequency_domain_data
    # Shape M, N, O
    windows = frequency_domain_omicron_windows(
        frequency_array=frequency_array,
        characteristic_frequencies=characteristic_frequencies,
        quality_factors=quality_factors,
    )
    # Shape M, N
    frequency_minus_characteristic_frequency_tiles = (
        frequency_array[:, None] - characteristic_frequencies[None, :]
    )
    # Shape M, N, O
    frequency_domain_data_windowed = frequency_domain_data[:, None, None] * windows
    # Shape P, M, N
    time_shift_tiles = jnp.exp(
        1j
        * 2
        * jnp.pi
        * frequency_minus_characteristic_frequency_tiles[None, :, :]
        * times[:, None, None]
    )
    # Shape P, N, O
    tile_timeseries = (
        jnp.sum(
            jnp.where(
                frequency_mask[None, :, None, None],
                frequency_domain_data_windowed[None, :, :, :]
                * time_shift_tiles[:, :, :, None],
                0,
            ),
            axis=1,
        )
        / duration
    )
    return jnp.abs(tile_timeseries) ** 2


def threshold_triggers(
    energy_in_tiles: jnp.ndarray,
    snr_threshold: float,
    maximum_triggers_per_segment: Optional[float] = None,
) -> jnp.ndarray:
    """Get a boolean array for whether given tiles pass an SNR threshold

    Parameters
    =========
        energy_in_tiles : jnp.ndarray
            The energy in each tile, of shape (P, N, O)
        snr_threshold : float
            The minimum SNR in a tile for it to pass
        maximum_triggers_per_segment : Optional

    Returns
    =======
        jnp.ndarray
            A boolean array on whether the energy in each tile passes the SNR threshold
    """
    if maximum_triggers_per_segment is None:
        maximum_triggers_per_segment = jnp.inf

    def _number_of_tiles_above_threshold_exceeds_maximum(snr_threshold):
        energy_threshold = snr_threshold**2 + 2
        tile_passes_threshold = energy_in_tiles > energy_threshold
        return jnp.sum(tile_passes_threshold) > maximum_triggers_per_segment

    def _increment_snr_threshold(snr_threshold):
        return snr_threshold + 0.5

    if _number_of_tiles_above_threshold_exceeds_maximum(snr_threshold):
        snr_threshold = jax.lax.while_loop(
            _number_of_tiles_above_threshold_exceeds_maximum,
            _increment_snr_threshold,
            snr_threshold,
        )
        logger.info(
            f"Limited number of points to {maximum_triggers_per_segment}, set new SNR threshold of {snr_threshold}"
        )

    energy_threshold = snr_threshold**2 + 2
    tile_passes_threshold = energy_in_tiles > energy_threshold
    return tile_passes_threshold


@jax.jit
def approximate_distance_between_tiles(
    tile_coordinates_1, tile_coordinates_2
) -> ArrayLike:
    """Compute the approximate distance between two tiles in the Omicron mismatch metric

    A first order approximation is used, since integration along the geodesic is infeasible.
    This approximation breaks down at larger distances, but if the scale of the approximation
    breakdown is sufficiently larger than the scale of the distance threshold this will be ok.

    Parameters
    ==========
        tile_coordinates_1 : jnp.ndarray
            The coordinates of the first tile in (time, characteristic_frequency, quality_factor) space
        tile_coordinates_2 : jnp.ndarray
            The coordinates of the second tile in (time, characteristic_frequency, quality_factor) space
    """
    tau_distance_squared = (
        4 * jnp.pi * (tile_coordinates_1[0] - tile_coordinates_2[0]) ** 2
    ) * (
        (tile_coordinates_1[1] ** 2) / (tile_coordinates_1[2] ** 2)
        + (tile_coordinates_2[1] ** 2) / (tile_coordinates_2[2] ** 2)
    )
    phi_distance_squared = ((tile_coordinates_1[1] - tile_coordinates_2[1]) ** 2) * (
        (2 + tile_coordinates_1[2] ** 2) / (4 * tile_coordinates_1[1] ** 2)
        + (2 + tile_coordinates_2[2] ** 2) / (4 * tile_coordinates_2[1] ** 2)
    )
    q_distance_squared = ((tile_coordinates_1[2] - tile_coordinates_2[2]) ** 2 / 2) * (
        (1 / tile_coordinates_1[2] ** 2) + (1 / tile_coordinates_2[2] ** 2)
    )
    return jnp.sqrt(
        (tau_distance_squared + phi_distance_squared + q_distance_squared) / 2
    )


def pairwise(f: Callable, xs: jnp.ndarray) -> jnp.ndarray:
    """A vmapped implementation of computing pairwise quantities.

    Taken directly from https://docs.jax.dev/en/latest/automatic-vectorization.html

    Parameters
    ==========
    f : Callable
        The callable funcion to map, should take as arguments two points, each
        an ArrayLike of the same shape (M,)
    xs : jnp.ndarray
        The points to map over, should be an array of shape (N, M) where N is the
        number of points and M is the dimension of the embedding space

    Returns
    =======
        jnp.ndarray
            An array of the value computed pairwise, of shape (N, N)
    """
    return jax.vmap(lambda x: jax.vmap(lambda y: f(x, y))(xs))(xs)


def cluster_thresholded_triggers(
    tiles_passing_threshold: jnp.ndarray,
    time_coordinates: jnp.ndarray,
    frequency_coordinates: jnp.ndarray,
    quality_factor_coordinates: jnp.ndarray,
    cluster_distance_threshold: float = 10.0,
) -> tuple[jnp.ndarray, JaxDBScan]:
    """Cluster a set of thresholded triggers according to their distance on the Omicron mismatch metric.

    Parameters
    ==========
        tiles_passing_threshold : jnp.ndarray
            A boolean array on whether the energy in each tile passes the SNR threshold, of shape (P, N, O)
        time_coordinates : jnp.ndarray
            The array of central times of the omicron tiles, of shape (P,)
        frequency_coordinates : jnp.ndarray
            The array of characteristic frequencies of the tiles ($\\phi$ in Robinet). Shape (N,)
        quality_factor_coordinates : jnp.ndarray
            The array of quality factors for the tiles. Shape (O,)
        cluster_distance_threshold : float
            The distance threshold for each cluster, as defined in DBSCAN documentation

    Returns
    =======
        jnp.ndarray
            The array of coordinates for tiles which passed the threshold, of shape (Q, 3) where
            Q is the number of tiles which passed
        DBSCAN
            The scikit-learn clustering object, with the passing tiles fitted
    """
    passing_indices = jnp.argwhere(tiles_passing_threshold)
    passing_coordinates = jnp.array(
        [
            time_coordinates[passing_indices[:, 0]],
            frequency_coordinates[passing_indices[:, 1]],
            quality_factor_coordinates[passing_indices[:, 2]],
        ]
    ).T
    passing_coordinate_distances = pairwise(
        approximate_distance_between_tiles, passing_coordinates
    )
    cluster = JaxDBScan(
        eps=cluster_distance_threshold,
        min_pts=10,
        metric="precomputed",
        memory_mode="standard",
        use_distributed=True,
    )
    cluster.fit(passing_coordinate_distances)
    return passing_coordinates, cluster


def get_max_snr_tile_for_clusters(
    energy_in_tiles: jnp.ndarray,
    tiles_passing_threshold: jnp.ndarray,
    passing_coordinates: jnp.ndarray,
    cluster: JaxDBScan,
) -> dict[int, tuple[float, jnp.ndarray]]:
    """For each cluster, identify the tile in that cluster with maximum energy

    Parameters
    =========
        energy_in_tiles : jnp.ndarray
            The energy in each tile, of shape (P, N, O)
        tiles_passing_threshold : jnp.ndarray
            A boolean array on whether the energy in each tile passes the SNR threshold, of shape (P, N, O)
        jnp.ndarray
            The array of coordinates for tiles which passed the threshold, of shape (Q, 3) where
            Q is the number of tiles which passed
        DBSCAN
            The scikit-learn clustering object, with the passing tiles fitted

    Returns

    """
    cluster_information = {}
    for cluster_index in jnp.unique(cluster.labels_):
        passing_tile_energies = energy_in_tiles[tiles_passing_threshold]
        cluster_max_energy_index = jnp.argmax(
            jnp.where(cluster.labels_ == cluster_index, passing_tile_energies, 0)
        )
        cluster_max_energy = passing_tile_energies[cluster_max_energy_index]
        cluster_max_snr = jnp.sqrt(cluster_max_energy - 2)
        cluster_max_energy_coordinates = passing_coordinates[cluster_max_energy_index]
        cluster_information[int(cluster_index)] = (
            cluster_max_snr,
            cluster_max_energy_coordinates,
        )
    return cluster_information


def scan_segment(
    time_domain_data: jnp.ndarray, omicron_configuration: OmicronConfiguration
) -> tuple[
    dict[int, tuple[float, jnp.ndarray]],
    jnp.ndarray,
    jnp.ndarray,
    JaxDBScan,
    tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray],
]:
    """Goes through all the steps of scanning a segment of time domain data with Omicron

    Parameters
    ==========
        time_domain_data : jnp.ndarray
            The array of time domain data to analyze
        omicron_configuration : OmicronConfiguration
            The OmicronConfiguration containing settings for running the analysis

    """
    resampled_time_domain_data = resample_timeseries(
        time_domain_data=time_domain_data,
        starting_sampling_frequency=omicron_configuration.starting_sampling_frequency,
        target_sampling_frequency=omicron_configuration.target_sampling_frequency,
        duration=omicron_configuration.duration,
    )

    whitened_time_domain_data, whitened_frequency_domain_data = whiten_timeseries(
        time_domain_data=resampled_time_domain_data,
        sampling_frequency=omicron_configuration.target_sampling_frequency,
        duration=omicron_configuration.duration,
        tukey_alpha=omicron_configuration.tukey_alpha,
        number_welch_segments=omicron_configuration.number_welch_segments,
        minimum_frequency=omicron_configuration.minimum_frequency,
        maximum_frequency=omicron_configuration.maximum_frequency,
    )

    logger.info("Generating Tiles")
    quality_factors, characteristic_frequencies, times = get_tiles(
        energy_loss_max=omicron_configuration.maximum_energy_loss,
        quality_factor_max=omicron_configuration.maximum_quality_factor,
        quality_factor_min=omicron_configuration.minimum_quality_factor,
        characteristic_frequency_max=omicron_configuration.maximum_characteristic_frequency,
        characteristic_frequency_min=omicron_configuration.minimum_characteristic_frequency,
        time_max=omicron_configuration.start_time
        + omicron_configuration.duration
        - omicron_configuration.tukey_alpha * omicron_configuration.duration / 2,
        time_min=omicron_configuration.start_time
        + omicron_configuration.tukey_alpha * omicron_configuration.duration / 2,
        max_number_time_samples=omicron_configuration.duration
        * omicron_configuration.target_sampling_frequency
        * (1 - omicron_configuration.tukey_alpha),
    )
    logger.info(
        f"Tile dimensions: {(len(times), len(characteristic_frequencies), len(quality_factors))}"
    )
    logger.info("Calculating energy in tiles")
    # energy_in_tiles = get_energy_in_tiles(
    #     whitened_time_domain_data,
    #     times=times,
    #     characteristic_frequencies=characteristic_frequencies,
    #     quality_factors=quality_factors,
    #     sampling_frequency=omicron_configuration.target_sampling_frequency,
    # ).block_until_ready()
    energy_in_tiles = get_energy_in_tiles_frequency_domain_data(
        whitened_frequency_domain_data,
        times=times,
        characteristic_frequencies=characteristic_frequencies,
        quality_factors=quality_factors,
        sampling_frequency=omicron_configuration.target_sampling_frequency,
    ).block_until_ready()

    print(energy_in_tiles[:5, :5, :5])
    logger.info("Thresholding triggers")
    tiles_passing_threshold = threshold_triggers(
        energy_in_tiles=energy_in_tiles,
        snr_threshold=omicron_configuration.snr_threshold,
        maximum_triggers_per_segment=omicron_configuration.maximum_triggers_per_segment,
    ).block_until_ready()
    logger.info(
        f"Number of triggers passing threshold: {jnp.sum(tiles_passing_threshold)}"
    )
    logger.info("Clustering triggers above threshold")
    passing_coordinates, cluster = cluster_thresholded_triggers(
        tiles_passing_threshold=tiles_passing_threshold,
        time_coordinates=times,
        frequency_coordinates=characteristic_frequencies,
        quality_factor_coordinates=quality_factors,
        cluster_distance_threshold=omicron_configuration.cluster_distance_threshold,
    )
    logger.info("Determining maximum energy tiles")
    maximum_energy_cluster_tiles = get_max_snr_tile_for_clusters(
        energy_in_tiles=energy_in_tiles,
        tiles_passing_threshold=tiles_passing_threshold,
        passing_coordinates=passing_coordinates,
        cluster=cluster,
    )
    return (
        maximum_energy_cluster_tiles,
        energy_in_tiles,
        passing_coordinates,
        cluster,
        (quality_factors, characteristic_frequencies, times),
    )
