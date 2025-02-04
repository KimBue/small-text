import unittest

from small_text.training.early_stopping import (
    EarlyStopping,
    NoopEarlyStopping,
    SequentialEarlyStopping
)


class NoopStoppingHandlerTest(unittest.TestCase):

    def test_stopping_handler_all(self):
        stopping_handler = NoopEarlyStopping()
        self.assertFalse(stopping_handler.check_early_stop(0, dict()))
        self.assertFalse(stopping_handler.check_early_stop(0, dict()))
        self.assertFalse(stopping_handler.check_early_stop(1, dict()))


class EarlyStoppingTest(unittest.TestCase):

    def test_check_early_stop_with_varying_metrics(self):
        stopping_handler = EarlyStopping('train_acc', patience=2)
        check_early_stop = stopping_handler.check_early_stop
        self.assertFalse(check_early_stop(1, {'valid_loss': 0.35, 'train_acc': 0.80}))
        self.assertFalse(check_early_stop(1, {'valid_loss': 0.34}))
        self.assertFalse(check_early_stop(1, {'valid_loss': 0.33}))
        self.assertFalse(check_early_stop(2, {'valid_loss': 0.35, 'train_acc': 0.81}))
        self.assertFalse(check_early_stop(2, {'valid_loss': 0.34}))
        self.assertFalse(check_early_stop(2, {'valid_loss': 0.35}))


class GeneralEarlyStoppingTest(object):

    def test_init_invalid_monitor(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported metric'):
            EarlyStopping('unknown_metric')

    def test_init_invalid_patience(self):
        with self.assertRaisesRegex(ValueError,
                                    'Invalid value encountered: "patience" needs to be'):
            EarlyStopping(self.get_monitor(), patience=0)

    def test_init_invalid_min_delta(self):
        with self.assertRaisesRegex(ValueError,
                                    'Invalid value encountered: "min_delta" needs to be'):
            EarlyStopping(self.get_monitor(), min_delta=-0.01)

    def test_check_early_stop_invalid_epoch(self):
        stopping_handler = EarlyStopping(self.get_monitor())
        with self.assertRaisesRegex(ValueError,
                                    'Argument "epoch" must be greater'):
            stopping_handler.check_early_stop(0, {self.get_monitor(): 0.25})


class LossBasedEarlyStoppingTest(object):

    def get_monitor(self):
        raise NotImplementedError('get_monitor() must be implemented')

    def test_init_default(self):
        stopping_handler = EarlyStopping(self.get_monitor())
        self.assertIsNotNone(stopping_handler.history)
        self.assertEqual((0,), stopping_handler.history.shape)
        self.assertEqual(self.get_monitor(), stopping_handler.monitor)
        self.assertEqual(1e-14, stopping_handler.min_delta)
        self.assertEqual(5, stopping_handler.patience)
        self.assertEqual(0, stopping_handler.threshold)

    def test_check_early_stop_loss_threshold(self):
        stopping_handler = EarlyStopping(self.get_monitor(), threshold=0.1,
                                         patience=2)
        self.assertTrue(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.05}))

        stopping_handler = EarlyStopping(self.get_monitor(), threshold=0.1,
                                         patience=2)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.2}))
        self.assertTrue(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.009}))

    def test_check_early_stop_loss_patience_and_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.065}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.068}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.067}))
        self.assertTrue(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.066}))

    def test_check_early_stop_loss_min_delta(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2, min_delta=0)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.04}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.035}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.033}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.031}))

        stopping_handler = EarlyStopping(self.get_monitor(), patience=2, min_delta=0.01)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.04}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.031}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.032}))
        self.assertTrue(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.031}))

    def test_check_early_stop_loss_patience_and_dont_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.04}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.031}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.029}))

    def test_check_early_stop_loss_patience_and_delta_dont_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=3)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.065}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.065}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.066}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.055}))

    def test_check_early_stop_loss_patience_and_dont_stop_extended(self):
        """Checks if an update of the best index is recognized, i.e. compares to the previous test
        this would stop but does not if a new best index is correctly recognized in epoch 1."""
        stopping_handler = EarlyStopping(self.get_monitor(), patience=3)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.180}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.193}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.160}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.170}))

    def test_check_early_stop_with_none_values_in_between(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.35}))
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.35}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.35}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertTrue(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.35}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): None}))


class EarlyStoppingValLossTest(unittest.TestCase,
                               GeneralEarlyStoppingTest,
                               LossBasedEarlyStoppingTest):

    def get_monitor(self):
        return 'val_loss'


class EarlyStoppingTrainLossTest(unittest.TestCase,
                                 GeneralEarlyStoppingTest,
                                 LossBasedEarlyStoppingTest):

    def get_monitor(self):
        return 'train_loss'


class AccuracyBasedEarlyStoppingTest(object):

    def get_monitor(self):
        raise NotImplementedError('monitor must be implemented')

    def test_init_default(self):
        stopping_handler = EarlyStopping(self.get_monitor())
        self.assertIsNotNone(stopping_handler.history)
        self.assertEqual((0,), stopping_handler.history.shape)
        self.assertEqual(self.get_monitor(), stopping_handler.monitor)
        self.assertEqual(1e-14, stopping_handler.min_delta)
        self.assertEqual(5, stopping_handler.patience)
        self.assertEqual(0, stopping_handler.threshold)

    def test_init_invalid_threshold(self):
        with self.assertRaisesRegex(ValueError,
                                    'Invalid value encountered: \"threshold\" needs to be'):
            EarlyStopping(self.get_monitor(), threshold=-0.01)

        with self.assertRaisesRegex(ValueError,
                                    'Invalid value encountered: \"threshold\" needs to be'):
            EarlyStopping(self.get_monitor(), threshold=1.01)

    def test_check_early_stop_acc_no_patience(self):
        with self.assertRaisesRegex(ValueError,
                                    'Invalid value encountered: \"patience\" needs to be'):
            EarlyStopping(self.get_monitor(), min_delta=0.01, patience=0)

    def test_check_early_stop_acc_threshold(self):
        stopping_handler = EarlyStopping(self.get_monitor(), threshold=0.9,
                                         patience=2)

        self.assertTrue(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.91}))

        stopping_handler = EarlyStopping(self.get_monitor(), threshold=0.9,
                                         patience=2)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.80}))
        self.assertTrue(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.91}))

    def test_check_early_stop_acc_patience_and_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.65}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.64}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.63}))
        self.assertTrue(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.65}))

    def test_check_early_stop_loss_min_delta(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2, min_delta=0)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.80}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.82}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.85}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.90}))

        stopping_handler = EarlyStopping(self.get_monitor(), patience=2, min_delta=0.01)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.89}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.89}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.89}))
        self.assertTrue(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.899}))

    def test_check_early_stop_acc_patience_and_dont_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.70}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.68}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.71}))

    def test_check_early_stop_val_acc_patience_and_dont_stop(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=3)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.65}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.65}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.66}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.55}))

    def test_check_early_stop_val_acc_patience_and_dont_stop_extended(self):
        """Checks if an update of the best index is recognized, i.e. compares to the previous test
        this would stop but does not if a new best index is correctly recognized in epoch 1."""
        stopping_handler = EarlyStopping(self.get_monitor(), patience=3)

        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.680}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.693}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.660}))
        self.assertFalse(stopping_handler.check_early_stop(4, {self.get_monitor(): 0.670}))

    def test_check_early_stop_with_none_values_in_between(self):
        stopping_handler = EarlyStopping(self.get_monitor(), patience=2)
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): 0.68}))
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(1, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.68}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): 0.68}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(2, {self.get_monitor(): None}))
        self.assertTrue(stopping_handler.check_early_stop(3, {self.get_monitor(): 0.68}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): None}))
        self.assertFalse(stopping_handler.check_early_stop(3, {self.get_monitor(): None}))


class EarlyStoppingValAccTest(unittest.TestCase,
                              GeneralEarlyStoppingTest,
                              AccuracyBasedEarlyStoppingTest):

    def get_monitor(self):
        return 'val_acc'


class EarlyStoppingTrainAccTest(unittest.TestCase,
                                GeneralEarlyStoppingTest,
                                AccuracyBasedEarlyStoppingTest):

    def get_monitor(self):
        return 'train_acc'


class SequentialEarlyStoppingTest(unittest.TestCase):

    def test_check_early_stop(self):
        stopping_handler = SequentialEarlyStopping([
            EarlyStopping('val_loss', patience=2),
            EarlyStopping('train_acc', patience=5)
        ])

        check_early_stop = stopping_handler.check_early_stop
        self.assertFalse(check_early_stop(1, {'val_loss': 0.07, 'train_acc': 0.68}))
        self.assertFalse(check_early_stop(2, {'val_loss': 0.08, 'train_acc': 0.69}))
        self.assertFalse(check_early_stop(3, {'val_loss': 0.07, 'train_acc': 0.70}))
        self.assertTrue(check_early_stop(4, {'val_loss': 0.07, 'train_acc': 0.70}))

    def test_check_early_stop_no_stop(self):
        stopping_handler = SequentialEarlyStopping([
            EarlyStopping('val_loss', patience=5),
            EarlyStopping('train_acc', patience=5)
        ])

        check_early_stop = stopping_handler.check_early_stop
        self.assertFalse(check_early_stop(1, {'val_loss': 0.07, 'train_acc': 0.68}))
        self.assertFalse(check_early_stop(2, {'val_loss': 0.08, 'train_acc': 0.69}))
        self.assertFalse(check_early_stop(3, {'val_loss': 0.07, 'train_acc': 0.70}))
        self.assertFalse(check_early_stop(4, {'val_loss': 0.07, 'train_acc': 0.70}))
