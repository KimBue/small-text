import logging
import numpy as np

from abc import ABC


class EarlyStoppingHandler(ABC):

    def check_early_stop(self, epoch, measured_values):
        """Checks if the training should be stopped early. The decision is made based on
        the masured values of one or more quantitative metrics over time.

        Parameters
        ----------
        epoch : int
            The number of the current epoch. Multiple checks per epoch are allowed.
        measure_values : dict of str to float
            A dictionary of measured values.
        """
        pass


class NoopEarlyStopping(EarlyStoppingHandler):
    """A no-operation early stopping handler which never stops. This is for developer
    convenience only, you will likely not need this in an application setting.

    .. versionadded:: 1.1.0
    """

    def check_early_stop(self, epoch, measured_values):
        """Checks if the training should be stopped early. The decision is made based on
        the masured values of one or more quantitative metrics over time.

        Parameters
        ----------
        epoch : int
            The number of the current epoch (1-indexed). Multiple checks per epoch are allowed.
        measured_values : dict of str to float
            A dictionary of measured values.
        """
        _unused = epoch, measured_values  # noqa:F841
        return False


class EarlyStopping(EarlyStoppingHandler):
    """A default early stopping implementation which supports stopping based on thresholds
    or based on (lack of) improvement.

    .. versionadded:: 1.1.0
    """
    def __init__(self, monitor, min_delta=1e-14, patience=5, threshold=0.0):
        """
        Parameters
        ----------
        monitor : {'valid_loss', 'valid_acc', 'train_loss', 'train_acc'}
            The measured value which will be monitored for early stopping.
        min_delta : float, default=1e-14
            The minimum absolute value to consider a change in the masured value as an
            improvement.
        patience : int, default=5
            The maxim number of steps (i.e. calls to `check_early_stop()`) which can yield no
            improvement.
        threshold : float, default=0.0
            If greater zero, then early stopping is triggered as soon as the current measured value
            crosses ('valid_acc', 'train_acc') or falls below ('valid_loss', 'train_loss')
            the given threshold.
        """
        self._validate_arguments(monitor, min_delta, patience, threshold)

        self.dtype = {
            'names': ['epoch', 'count', 'train_acc', 'train_loss', 'val_acc', 'val_loss'],
            'formats': [int, int, float, float, float, float]
        }

        self.monitor = monitor
        self.min_delta = min_delta
        self.patience = patience
        self.threshold = threshold

        self.index_best = -1
        self.history = np.empty((0,), dtype=self.dtype)

    def _validate_arguments(self, monitor, min_delta, patience, threshold):
        if monitor not in ['train_acc', 'train_loss', 'val_acc', 'val_loss']:
            raise ValueError(f'Unsupported metric "{monitor}". '
                             'Valid values: [train_acc, train_loss, val_acc, val_loss]')

        if min_delta < 0:
            raise ValueError('Invalid value encountered: '
                             '"min_delta" needs to be greater than zero.')

        if patience <= 0:
            raise ValueError('Invalid value encountered: '
                             '"patience" needs to be greater or equal 1.')

        if '_acc' in monitor and (threshold < 0.0 or threshold > 1.0):
            raise ValueError('Invalid value encountered: '
                             '"threshold" needs to be within the interval [0, 1] '
                             'for accuracy metrics.')

    def check_early_stop(self, epoch, measured_values):
        """Checks if the training should be stopped early. The decision is made based on
        the masured values of one or more quantitative metrics over time.

        1. Returns `True` if the threshold is crossed/undercut (for accuracy/loss respectively).
        2. Checks for an improvement and returns `True` if patience has been execeeded.
        3. Otherwise, return `False`.

        Parameters
        ----------
        epoch : int
            The number of the current epoch (1-indexed). Multiple checks per epoch are allowed.
        measured_values : dict of str to float
            A dictionary of measured values.
        """
        if epoch <= 0:
            raise ValueError('Argument "epoch" must be greater than zero.')

        self.history = self.add_to_history(epoch, measured_values)

        greater_is_better = '_acc' in self.monitor
        monitor_sign = 1 if greater_is_better else -1

        measured_value = measured_values.get(self.monitor, None)
        has_crossed_threshold = measured_value is not None and \
            np.sign(measured_value - self.threshold) == monitor_sign
        if self.threshold > 0 and has_crossed_threshold:
            logging.debug(f'Early stopping: Threshold exceeded. '
                          f'[value={measured_values[self.monitor]}, threshold={self.threshold}]')
            return True
        elif measured_value is None:
            return False

        if len(self.history) == 1:
            self.index_best = 0
            return False

        return self._check_for_improvement(measured_values, monitor_sign)

    def _check_for_improvement(self, measured_values, monitor_sign):
        previous_best = self.history[self.monitor][self.index_best]
        index_last = self.history.shape[0] - 1

        delta = measured_values[self.monitor] - previous_best
        delta_sign = np.sign(delta)

        if self.min_delta > 0:
            improvement = delta_sign == monitor_sign and np.abs(delta) >= self.min_delta
        else:
            improvement = delta_sign == monitor_sign

        if improvement:
            self.index_best = index_last
            return False
        else:
            history_since_previous_best = self.history[self.index_best+1:][self.monitor]
            rows_not_nan = np.logical_not(np.isnan(history_since_previous_best))
            if rows_not_nan.sum() > self.patience:
                logging.debug(f'Early stopping: Patience exceeded.'
                              f'{{value={index_last-self.index_best}, patience={self.patience}}}')
                return True
            return False

    def add_to_history(self, epoch, measured_values):
        count = (self.history['epoch'] == epoch).sum()
        tuple_measured_values = (measured_values.get('train_acc', None),
                                 measured_values.get('train_loss', None),
                                 measured_values.get('val_acc', None),
                                 measured_values.get('val_loss', None))
        return np.append(self.history,
                         np.array((epoch, count) + tuple_measured_values, dtype=self.dtype))


class SequentialEarlyStopping(EarlyStoppingHandler):
    """A sequential early stopping handler which bases its response on a list of sub handlers.
    As long as one early stopping handler returns `True` the aggregated response will be `True`,
    i.e. the answer is the list of sub answers combined by a logical or.

    .. versionadded:: 1.1.0
    """
    def __init__(self, early_stopping_handlers):
        """
        Parameters
        ----------
        early_stopping_handlers : list of EarlyStoppingHandler
            A list of early stopping (sub-)handlers.
        """
        self.early_stopping_handlers = early_stopping_handlers

    def check_early_stop(self, epoch, measured_values):
        """Checks if the training should be stopped early. The decision is made based on
        the masured values of one or more quantitative metrics over time.

        Parameters
        ----------
        epoch : int
            The number of the current epoch (1-indexed). Multiple checks per epoch are allowed.
        measured_values : dict of str to float
            A dictionary of measured values.
        """
        results = []
        for early_stopping_handler in self.early_stopping_handlers:
            results.append(early_stopping_handler.check_early_stop(epoch, measured_values))
        return np.any(results)
