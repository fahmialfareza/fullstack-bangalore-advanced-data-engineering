"""Latihan Sesi 16. Data sintetis; tidak mengakses atau mengubah lake MinIO.

Jalankan dari folder sesi16. Contoh:
    python lab/spark_lab.py --experiment join --hold-ui
Hasil setiap run disimpan pada folder baru di lab/outputs.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def canonical(rows):
    """Hasil lab kecil dan berupa integer; seluruh nilai dapat dibandingkan persis."""
    return sorted(tuple(row) for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', choices=['join', 'partitions', 'aqe', 'cache', 'skew', 'failure'], default='join')
    parser.add_argument('--rows', type=int, default=300_000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--master', default='local[2]')
    parser.add_argument('--hold-ui', action='store_true')
    args = parser.parse_args()
    if args.rows < 1000 or args.repeats < 1:
        parser.error('--rows minimal 1000 dan --repeats minimal 1')

    # Konfigurasi hanya berlaku untuk proses lab ini.
    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    os.environ.setdefault('PYSPARK_PYTHON', sys.executable)
    import pyspark
    # Pakai JAR dari paket yang sama, bukan SPARK_HOME proyek lain.
    os.environ['SPARK_HOME'] = str(Path(pyspark.__file__).resolve().parent)
    # JAVA_HOME lama dapat berbeda dari java yang terlihat di terminal.
    # Pilihan ini hanya berlaku di proses lab dan tidak mengubah environment Windows.
    java = shutil.which('java')
    if not java:
        parser.error('Java tidak ditemukan pada PATH. Siapkan Java 17 sebelum menjalankan lab.')
    probe = subprocess.run([java, '-XshowSettings:properties', '-version'],
                           capture_output=True, text=True, check=False)
    info = probe.stdout + probe.stderr
    java_home = re.search(r'^\s*java.home\s*=\s*(.+)$', info, re.MULTILINE)
    java_major = re.search(r'^\s*java.specification.version\s*=\s*(\d+)', info, re.MULTILINE)
    if not java_home or not java_major or int(java_major.group(1)) < 17:
        parser.error('Lab membutuhkan Java 17+. Periksa java -version pada terminal yang sama.')
    os.environ['JAVA_HOME'] = java_home.group(1).strip()
    from pyspark.sql import SparkSession, functions as F

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out = Path(__file__).resolve().parent / 'outputs' / f'{run_id}_{args.experiment}'
    out.mkdir(parents=True, exist_ok=False)
    spark = (SparkSession.builder.appName(f'Sesi16-{args.experiment}')
             .master(args.master)
             .config('spark.sql.shuffle.partitions', '8')
             .config('spark.sql.autoBroadcastJoinThreshold', '-1')
             .config('spark.sql.adaptive.enabled', 'false')
             .config('spark.ui.bindAddress', '0.0.0.0')
             .getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    print(f'Spark UI: {spark.sparkContext.uiWebUrl}', flush=True)
    print(f'Folder hasil: {out}', flush=True)

    def write_json(name, value):
        (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

    def save_plan(q, name):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            q.explain('formatted')
        (out / name).write_text(buffer.getvalue(), encoding='utf-8')

    def aggregate(df):
        return (df.groupBy('region')
                .agg(F.sum('amount').alias('revenue'), F.count('*').alias('orders'))
                .select('region', 'revenue', 'orders'))

    def configure(aqe=False, partitions=8):
        spark.conf.set('spark.sql.adaptive.enabled', str(aqe).lower())
        spark.conf.set('spark.sql.shuffle.partitions', str(partitions))
        spark.conf.set('spark.sql.autoBroadcastJoinThreshold', '-1')
        spark.conf.set('spark.sql.adaptive.autoBroadcastJoinThreshold', '-1')

    try:
        # Tidak memerlukan Python UDF, file sumber, atau jaringan.
        orders = (spark.range(args.rows, numPartitions=4)
                  .select(F.col('id').alias('order_id'),
                          (F.col('id') % 1000).alias('customer_id'),
                          ((F.col('id') % 97 + 1) * 100).alias('amount')))
        customers = (spark.range(1000, numPartitions=2)
                     .select(F.col('id').alias('customer_id'),
                             (F.col('id') % 5).cast('int').alias('region')))
        direct = orders.withColumn('region', (F.col('customer_id') % 5).cast('int'))
        reference = canonical(aggregate(direct).collect())
        write_json('reference.json', reference)
        java_version = spark.sparkContext._jvm.java.lang.System.getProperty('java.version')
        write_json('environment.json', {
            'spark_version': spark.version, 'python_version': sys.version,
            'java_version': java_version, 'platform': platform.platform(),
            'master': args.master, 'rows': args.rows, 'repeats': args.repeats,
            'app_id': spark.sparkContext.applicationId,
            'ui_url': spark.sparkContext.uiWebUrl,
            'timer_scope': 'action only; cache candidate includes materialization and three actions',
            'limitations': ['synthetic data', 'local default; not a production cluster benchmark',
                            'OS cache and JVM state are not reset between trials']})

        if args.experiment == 'failure':
            wrong = canonical(aggregate(direct.filter('region != 0')).collect())
            caught = wrong != reference
            write_json('failure.json', {'caught': caught, 'cause': 'region 0 removed',
                                       'expected': reference, 'actual': wrong})
            if not caught:
                raise AssertionError('Pemeriksaan gagal menangkap hasil yang sengaja diubah')
            print('PASS: perbedaan hasil tertangkap (caught=true).')
            return

        if args.experiment == 'skew':
            configure()
            skewed = orders.withColumn('customer_id',
                F.when(F.col('order_id') % 10 < 8, F.lit(0)).otherwise(F.col('customer_id')))
            distribution = (skewed.repartition(8, 'customer_id')
                            .select(F.spark_partition_id().alias('partition_id'))
                            .groupBy('partition_id').count())
            save_plan(distribution, 'plan_before.txt')
            rows = sorted([r.asDict() for r in distribution.collect()], key=lambda r:r['partition_id'])
            save_plan(distribution, 'plan_after.txt')
            assert sum(r['count'] for r in rows) == args.rows
            write_json('distribution.json', rows)
            print('Jumlah baris per partisi:', rows)
            return

        variants = {
            'join': ['baseline', 'broadcast'],
            'partitions': ['p2', 'p8', 'p32'],
            'aqe': ['aqe_off', 'aqe_on'],
            'cache': ['no_cache', 'cache'],
        }[args.experiment]

        def one_trial(variant, repeat, save=True):
            spark.catalog.clearCache()
            configure(aqe=(variant == 'aqe_on'),
                      partitions=int(variant[1:]) if args.experiment == 'partitions' else
                      (64 if args.experiment == 'aqe' else 8))
            spark.sparkContext.setJobGroup(f'{variant}-{repeat}', f'{args.experiment}: {variant}, run {repeat}')
            extra = {}
            if args.experiment == 'cache':
                fingerprint = F.col('order_id').cast('string')
                for _ in range(4):
                    fingerprint = F.sha2(fingerprint, 256)
                base = direct.withColumn('fingerprint', fingerprint)
                if variant == 'cache':
                    base = base.cache()
                def make_query(k):
                    # Nilai fingerprint ikut digunakan agar transformasi tidak dibuang optimizer.
                    return (base.filter(F.col('order_id') % 3 == k).groupBy('region')
                            .agg(F.sum('amount').alias('revenue'),
                                 F.sum(F.length('fingerprint')).alias('fingerprint_chars')))
                expected_queries = [canonical(make_query(k).collect()) for k in range(3)] if variant=='no_cache' and repeat=='warmup' else None
                if expected_queries is not None:
                    cache_reference[:] = expected_queries
                started = time.perf_counter()
                if variant == 'cache':
                    base.count()
                    extra['materialize_seconds'] = time.perf_counter() - started
                results = []
                for k in range(3):
                    q = make_query(k)
                    results.append(q.collect())
                seconds = time.perf_counter() - started
                # canonical() dan perbandingan dilakukan sesudah timer dihentikan.
                assert [canonical(rows) for rows in results] == cache_reference, 'Hasil cache berubah'
                if save:
                    save_plan(q, f'{variant}_{repeat}_plan_after.txt')
                base.unpersist(blocking=True)
            else:
                dim = F.broadcast(customers) if variant == 'broadcast' else customers
                q = aggregate(orders.join(dim, 'customer_id', 'inner'))
                if save:
                    save_plan(q, f'{variant}_{repeat}_plan_before.txt')
                started = time.perf_counter()
                rows = q.collect()
                seconds = time.perf_counter() - started
                assert canonical(rows) == reference, f'Hasil berubah pada {variant}'
                if save:
                    save_plan(q, f'{variant}_{repeat}_plan_after.txt')
            print(f'{variant:12} run={repeat}: {seconds:.3f}s; hasil sama', flush=True)
            return {'variant': variant, 'repeat': repeat, 'total_seconds': seconds,
                    'correct': True, **extra}

        cache_reference = []
        for variant in variants:
            one_trial(variant, 'warmup', save=False)
        trials = []
        for repeat in range(args.repeats):
            offset = repeat % len(variants)
            for variant in variants[offset:] + variants[:offset]:
                trials.append(one_trial(variant, repeat+1))
        with (out/'trials.csv').open('w', newline='', encoding='utf-8') as handle:
            fields = ['variant','repeat','total_seconds','correct','materialize_seconds']
            writer=csv.DictWriter(handle,fieldnames=fields)
            writer.writeheader();writer.writerows(trials)
        summary=[]
        for variant in variants:
            values=[r['total_seconds'] for r in trials if r['variant']==variant]
            summary.append({'variant':variant,'median_seconds':statistics.median(values),
                            'min_seconds':min(values),'max_seconds':max(values),
                            'runs':len(values),'correct':True})
        write_json('summary.json',summary)
        write_json('trials.json',trials)
        print(json.dumps(summary,indent=2))
    finally:
        if args.hold_ui:
            try:
                input('\nBuka Spark UI sekarang. Tekan Enter untuk menutup aplikasi... ')
            except EOFError:
                pass
        spark.stop()


if __name__ == '__main__':
    main()
