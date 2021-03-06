"""Analysis functions (mostly for psychophysics data).
"""

import warnings
import numpy as np
import scipy.stats as ss
from scipy.optimize import curve_fit
from functools import partial
from collections import namedtuple


def press_times_to_hmfc(presses, targets, foils, tmin, tmax,
                        return_type='counts'):
    """Convert press times to hits/misses/FA/CR

    Parameters
    ----------
    presses : list
        List of press times (in seconds).
    targets : list
        List of target times.
    foils : list | None
        List of foil (distractor) times.
    tmin : float
        Minimum time after a target/foil to consider a press.
    tmax : float
        Maximum time after a target/foil to consider a press.
    return_type : str
        Currently only ``'counts'`` is supported. Eventually we will
        add rection-time support as well.

    Returns
    -------
    hmfco : list
        Hits, misses, false alarms, correct rejections, and other presses
        (not within the window for a target or a masker).

    Notes
    -----
    Multiple presses within a single "target window" (i.e., between ``tmin``
    and ``tmax`` of a target) or "masker window" get treated as a single
    press by this function. However, there is no such de-bouncing of responses
    to "other" times.
    """
    # Sanity check that targets and foils don't overlap (due to tmin/tmax)
    targets = np.atleast_1d(targets) + tmin
    foils = np.atleast_1d(foils) + tmin
    dur = float(tmax - tmin)
    assert dur > 0
    presses = np.sort(np.atleast_1d(presses))
    assert targets.ndim == foils.ndim == presses.ndim == 1
    all_times = np.concatenate(([-np.inf], targets, foils, [np.inf]))
    order = np.argsort(all_times)
    inv_order = np.argsort(order)
    all_times = all_times[order]
    if not np.all(all_times[:-1] + dur <= all_times[1:]):
        raise ValueError('Analysis windows for targets and foils overlap')
    # Let's just loop (could probably be done with vector math, but it's
    # too hard and unlikely to be correct)
    locs = np.searchsorted(all_times, presses, 'right')
    if len(locs) > 0:
        assert locs.max() < len(all_times)  # should be True b/c of np.inf
        assert locs.min() >= 1

    # figure out which presses were to target or masker (valid_idx)
    in_window = (presses <= all_times[locs - 1] + dur)
    valid_idx = np.where(in_window)[0]
    n_other = np.sum(~in_window)

    # figure out which of valid presses were to target or masker
    used = np.unique(locs[valid_idx])  # unique to remove double-presses
    orig_places = (inv_order[used - 1] - 1)
    n_hit = sum(orig_places < len(targets))
    n_fa = len(used) - n_hit
    n_miss = len(targets) - n_hit
    n_cr = len(foils) - n_fa
    return n_hit, n_miss, n_fa, n_cr, n_other


def logit(prop, max_events=None):
    """Convert proportion (expressed in the range [0, 1]) to logit.

    Parameters
    ----------
    prop : float | array-like
        the occurrence proportion.
    max_events : int | array-like | None
        the number of events used to calculate ``prop``. Used in a correction
        factor for cases when ``prop`` is 0 or 1, to prevent returning ``inf``.
        If ``None``, no correction is done, and ``inf`` or ``-inf`` may result.

    Returns
    -------
    lgt : ``numpy.ndarray``, with shape matching ``numpy.array(prop).shape``.
    """
    prop = np.atleast_1d(prop).astype(float)
    if np.any([prop > 1, prop < 0]):
        raise ValueError('Proportions must be in the range [0, 1].')
    if max_events is not None:
        # add equivalent of half an event to 0s, and subtract same from 1s
        max_events = np.atleast_1d(max_events) * np.ones_like(prop)
        corr_factor = 0.5 / max_events
        for loc in zip(*np.where(prop == 0)):
            prop[loc] = corr_factor[loc]
        for loc in zip(*np.where(prop == 1)):
            prop[loc] = 1 - corr_factor[loc]
    return np.log(prop / (np.ones_like(prop) - prop))


def sigmoid(x, lower=0., upper=1., midpt=0., slope=1.):
    """Calculate sigmoidal values along the x-axis

    Parameters
    ----------
    x : array-like
        x-values to calculate the sigmoidal values from.
    lower : float
        The lower y-asymptote.
    upper : float
        The upper y-asymptote.
    midpt : float
        The x-value that obtains 50% between the lower and upper asymptote.
    slope : float
        The slope of the sigmoid.

    Returns
    -------
    y : array
        The y-values of the sigmoid evaluated at x.
    """
    x = np.asarray(x)
    lower = float(lower)
    upper = float(upper)
    midpt = float(midpt)
    slope = float(slope)
    y = (upper - lower) / (1 + np.exp(-slope * (x - midpt))) + lower
    return y


def fit_sigmoid(x, y, p0=None, fixed=()):
    """Fit a sigmoid to summary data

    Given a set of average values ``y`` (e.g., response probabilities) as a
    function of a variable ``x`` (e.g., presented target level), this
    will estimate the underlying sigmoidal response. Note that the fitting
    function can be sensitive to the shape of the data, so always inspect
    your results.

    Parameters
    ----------
    x : array-like
        x-values along the sigmoid.
    y : array-like
        y-values at each location in the sigmoid.
    p0 : array-like | None
        Initial guesses for the fit. Can be None to estimate all parameters,
        or members of the array can be None to have these automatically
        estimated.
    fixed : list of str
        Which parameters should be fixed.

    Returns
    -------
    lower, upper, midpt, slope : floats
        See expyfun.analyze.sigmoid for descriptions.
    """
    # Initial estimates
    x = np.asarray(x)
    y = np.asarray(y)
    k = 2 * 4. / (np.max(x) - np.min(x))
    if p0 is None:
        p0 = [None] * 4
    p0 = list(p0)
    for ii, p in enumerate([np.min(y), np.max(y),
                            np.mean([np.max(x), np.min(x)]), k]):
        p0[ii] = p if p0[ii] is None else p0[ii]
    p0 = np.array(p0, dtype=np.float64)
    if p0.size != 4 or p0.ndim != 1:
        raise ValueError('p0 must have 4 elements, or be None')

    # Fixing values
    p_types = ('lower', 'upper', 'midpt', 'slope')
    for f in fixed:
        if f not in p_types:
            raise ValueError('fixed {0} not in parameter list {1}'
                             ''.format(f, p_types))
    fixed = np.array([(True if f in fixed else False) for f in p_types], bool)

    kwargs = dict()
    idx = list()
    keys = list()
    for ii, key in enumerate(p_types):
        if fixed[ii]:
            kwargs[key] = p0[ii]
        else:
            keys.append(key)
            idx.append(ii)
    p0 = p0[idx]
    if len(idx) == 0:
        raise RuntimeError('cannot fit with all fixed values')

    def wrapper(*args):
        assert len(args) == len(keys) + 1
        for key, arg in zip(keys, args[1:]):
            kwargs[key] = arg
        return sigmoid(args[0], **kwargs)

    out = curve_fit(wrapper, x, y, p0=p0)[0]
    assert len(idx) == len(out)
    for ii, o in zip(idx, out):
        kwargs[p_types[ii]] = o
    return namedtuple('params', p_types)(**kwargs)


def rt_chisq(x, axis=None):
    """Chi square fit for reaction times (a better summary statistic than mean)

    Parameters
    ----------
    x : array-like
        Reaction time data to fit.

    axis : int | None
        The axis along which to calculate the chi-square fit. If none, ``x``
        will be flattened before fitting.

    Returns
    -------
    peak : float | array-like
        The peak(s) of the fitted chi-square probability density function(s).

    Notes
    -----
    Verify that it worked by plotting pdf vs hist (for 1-dimensional x)::

        >>> import numpy as np
        >>> from scipy import stats as ss
        >>> import matplotlib.pyplot as plt
        >>> plt.ion()
        >>> x = np.abs(np.random.randn(10000) + 1)
        >>> lsp = np.linspace(np.floor(np.amin(x)), np.ceil(np.amax(x)), 100)
        >>> df, loc, scale = ss.chi2.fit(x, floc=0)
        >>> pdf = ss.chi2.pdf(lsp, df, scale=scale)
        >>> plt.plot(lsp, pdf)
        >>> plt.hist(x, normed=True)
    """
    x = np.asarray(x)
    if np.any(np.less(x, 0)):  # save the user some pain
        raise ValueError('x cannot have negative values')
    if axis is None:
        df, _, scale = ss.chi2.fit(x, floc=0)
    else:
        fit = partial(ss.chi2.fit, floc=0)
        params = np.apply_along_axis(fit, axis=axis, arr=x)  # df, loc, scale
        pmut = np.concatenate((np.atleast_1d(axis),
                               np.delete(np.arange(x.ndim), axis)))
        df = np.transpose(params, pmut)[0]
        scale = np.transpose(params, pmut)[2]
    quartiles = np.percentile(x, (25, 75))
    whiskers = quartiles + np.array((-1.5, 1.5)) * np.diff(quartiles)
    n_bad = np.sum(np.logical_or(np.less(x, whiskers[0]),
                                 np.greater(x, whiskers[1])))
    if n_bad > 0:
        warnings.warn('{0} likely bad values in x (of {1})'
                      ''.format(n_bad, x.size))
    peak = np.maximum(0, (df - 2)) * scale
    return peak


def dprime(hmfc, zero_correction=True):
    """Estimates d-prime, with optional correction factor to avoid infinites.

    Parameters
    ----------
    hmfc : array-like
        Hits, misses, false-alarms, and correct-rejections, in that order, as
        array-like data with last dimension having size 4.
    zero_correction : bool
        Whether to add a correction factor of 0.5 to each category to prevent
        division-by-zero leading to infinite d-prime values.

    Returns
    -------
    dp : array-like
        Array of dprimes with shape ``hmfc.shape[:-1]``.

    Notes
    -----
    For two-alternative forced-choice tasks, it is recommended to enter correct
    trials as hits and incorrect trials as false alarms, and enter misses and
    correct rejections as 0. An alternative is to use ``dprime_2afc()``, which
    wraps to ``dprime()`` and does this assignment for you.
    """
    hmfc = _check_dprime_inputs(hmfc)
    a = 0.5 if zero_correction else 0.0
    dp = ss.norm.ppf((hmfc[..., 0] + a) /
                     (hmfc[..., 0] + hmfc[..., 1] + 2 * a)) - \
        ss.norm.ppf((hmfc[..., 2] + a) /
                    (hmfc[..., 2] + hmfc[..., 3] + 2 * a))
    return dp


def dprime_2afc(hm, zero_correction=True):
    """Estimates d-prime for two-alternative forced-choice paradigms.

    Parameters
    ----------
    hm : array-like
        Correct trials (hits) and incorrect trials (misses), in that order, as
        array-like data with last dimension having size 4.
    zero_correction : bool
        Whether to add a correction factor of 0.5 to each category to prevent
        division-by-zero leading to infinite d-prime values.

    Returns
    -------
    dp : array-like
        Array of dprimes with shape ``hmfc.shape[:-1]``.
    """
    hmfc = _check_dprime_inputs(hm, True)
    return dprime(hmfc, zero_correction)


def _check_dprime_inputs(hmfc, tafc=False):
    """Formats input to dprime() and dprime_2afc().

    Parameters
    ----------
    hmfc : array-like
        Hit, miss, false-alarm, correct-rejection; or hit, miss for 2AFC.
    tafc : bool
        Is this a 2AFC design?
    """
    hmfc = np.asarray(hmfc)
    if tafc:
        if hmfc.shape[-1] != 2:
            raise ValueError('Array must have last dimension 2.')
    else:
        if hmfc.shape[-1] != 4:
            raise ValueError('Array must have last dimension 4')
    if tafc:
        z = np.zeros(hmfc.shape[:-1] + (4,), hmfc.dtype)
        z[..., [0, 2]] = hmfc
        hmfc = z
    if hmfc.dtype not in (np.int64, np.int32):
        warnings.warn('Argument (%s) to dprime() cast to np.int64; floating '
                      'point values will have been truncated.' % hmfc.dtype)
        hmfc = hmfc.astype(np.int64)
    return hmfc
