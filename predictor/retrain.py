"""retrain.py — Full ATD model retraining pipeline.

Runs all steps in sequence (or a subset via --steps).  Each step maps
1-to-1 to a notebook in notebooks/.

Usage
-----
# Run the full pipeline
python predictor/retrain.py

# Run specific steps only
python predictor/retrain.py --steps 10 11 12 13

# Run from step 12 onwards (skip slow feature engineering)
python predictor/retrain.py --steps 12 13 13.2 14 15

# Change XGBoost feature budget
python predictor/retrain.py --top-n 20

# Override data / model directories
python predictor/retrain.py --data-dir /mnt/data --model-dir /mnt/model
"""
import argparse
import logging
import time
from pathlib import Path

# ── Step imports ──────────────────────────────────────────────────────────
from step_10_data_cleaning        import run as run_10
from step_11_feature_engineering  import run as run_11
from step_12_train_test_split     import run as run_12
from step_12_5_normalization      import run as run_12_5
from step_13_model_training       import run as run_13
from step_13_2_xgboost_top_features import run as run_13_2
from step_14_model_evaluation     import run as run_14
from step_15_model_export         import run as run_15

ALL_STEPS = ['10', '11', '12', '12.5', '13', '13.2', '14', '15']

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Retrain the Uber Eats ATD prediction model.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--steps',
        nargs='+',
        default=ALL_STEPS,
        choices=ALL_STEPS,
        metavar='STEP',
        help=(
            'Steps to run (default: all). '
            f'Choices: {", ".join(ALL_STEPS)}'
        ),
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=15,
        help='Top-N features for XGBoost step 13.2 (default: 15)',
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=None,
        help='Override path to the data/ directory',
    )
    parser.add_argument(
        '--model-dir',
        type=Path,
        default=None,
        help='Override path to the model/ directory',
    )
    return parser.parse_args()


def _fmt(seconds: float) -> str:
    """Format elapsed seconds as mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}'


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    args      = _parse_args()
    root      = Path(__file__).parent.parent
    data_dir  = args.data_dir  or root / 'data'
    model_dir = args.model_dir or root / 'model'
    steps     = args.steps

    logger.info('=' * 60)
    logger.info('ATD Retraining Pipeline')
    logger.info('  data_dir  : %s', data_dir)
    logger.info('  model_dir : %s', model_dir)
    logger.info('  steps     : %s', ', '.join(steps))
    logger.info('  top_n     : %s', args.top_n)
    logger.info('=' * 60)

    pipeline_start = time.perf_counter()
    results        = {}

    def _run_step(label: str, fn, **kwargs) -> dict:
        logger.info('── Step %s starting ──', label)
        t0     = time.perf_counter()
        result = fn(data_dir=data_dir, model_dir=model_dir, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.info('── Step %s done in %s ──', label, _fmt(elapsed))
        return result

    if '10' in steps:
        results['10'] = _run_step('10 · Data Cleaning', run_10)

    if '11' in steps:
        results['11'] = _run_step(
            '11 · Feature Engineering', run_11
        )

    if '12' in steps:
        results['12'] = _run_step(
            '12 · Train/Val/Test Split', run_12
        )

    if '12.5' in steps:
        results['12.5'] = _run_step(
            '12.5 · MinMax Normalization', run_12_5
        )

    if '13' in steps:
        results['13'] = _run_step(
            '13 · LightGBM Training', run_13
        )

    if '13.2' in steps:
        results['13.2'] = _run_step(
            '13.2 · XGBoost Top-N',
            run_13_2,
            top_n=args.top_n,
        )

    if '14' in steps:
        results['14'] = _run_step(
            '14 · Model Evaluation', run_14
        )

    if '15' in steps:
        results['15'] = _run_step(
            '15 · Model Export', run_15
        )

    total = time.perf_counter() - pipeline_start
    logger.info('=' * 60)
    logger.info('Pipeline complete in %s', _fmt(total))

    # ── Final summary ─────────────────────────────────────────────────────
    if '13' in results:
        r = results['13']
        logger.info(
            'LightGBM  val_mae=%.3f  val_rmse=%.3f  val_r²=%.4f',
            r['val_mae'], r['val_rmse'], r['val_r2'],
        )
    if '13.2' in results:
        r = results['13.2']
        logger.info(
            'XGBoost   val_mae=%.3f  val_rmse=%.3f  val_r²=%.4f  '
            'delta_vs_lgbm=%+.3f',
            r['val_mae'], r['val_rmse'], r['val_r2'], r['mae_delta'],
        )
    if '14' in results:
        r = results['14']
        logger.info(
            'Test       mae=%.3f  rmse=%.3f  r²=%.4f',
            r['test_mae'], r['test_rmse'], r['test_r2'],
        )
    if '15' in results:
        r = results['15']
        logger.info(
            'Scored dataset: %s rows  sla_rate=%.1f%%',
            f'{r["n_rows"]:,}', r['sla_rate'],
        )
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
