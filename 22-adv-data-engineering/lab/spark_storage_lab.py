"""Praktik spill, small files, penggunaan resource, dan laporan Sesi 16.

Notebook memanggil fungsi yang sama dengan CLI ini. Semua data sintetis lokal.
Contoh: python lab/spark_storage_lab.py --rows 10000 --repeats 3
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
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
from urllib.parse import quote
from urllib.request import urlopen
from uuid import uuid4


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def api_json(spark, suffix):
    """Membaca metrik dari aplikasi Spark milik latihan ini."""
    sc = spark.sparkContext
    url = f'{sc.uiWebUrl}/api/v1/applications/{quote(sc.applicationId, safe="")}/{suffix}'
    with urlopen(url, timeout=20) as response:
        return json.load(response)


def measure(spark, out, label, action):
    """Waktu action dipisahkan dari pembacaan REST API dan validasi hasil."""
    sc = spark.sparkContext
    group = f'{label}-{uuid4().hex[:8]}'
    sc.setJobGroup(group, label)
    try:
        start = time.perf_counter()
        result = action()
        seconds = time.perf_counter() - start
    finally:
        for key in ('spark.jobGroup.id', 'spark.job.description', 'spark.job.interruptOnCancel'):
            sc.setLocalProperty(key, None)
    tracker = sc.statusTracker()
    job_ids = list(tracker.getJobIdsForGroup(group))
    stage_ids = set()
    for job in job_ids:
        info = tracker.getJobInfo(job)
        if info is not None:
            stage_ids.update(int(x) for x in info.stageIds)
    if not stage_ids:
        raise RuntimeError(f'Tidak menemukan stage untuk {label}; metrik tidak boleh dianggap nol.')
    # Listener UI dapat tertinggal sesaat setelah action selesai.
    for attempt in range(30):
        stages = api_json(spark, 'stages')
        chosen = []
        for sid in sorted(stage_ids):
            candidates = [s for s in stages if s['stageId'] == sid and s['status'] == 'COMPLETE']
            if candidates:
                chosen.append(max(candidates, key=lambda s: s['attemptId']))
        if len(chosen) == len(stage_ids):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f'Metrik stage belum lengkap untuk {label}.')
    tasks = []
    for stage in chosen:
        sid, aid = stage['stageId'], stage['attemptId']
        tasks.extend(api_json(spark, f'stages/{sid}/{aid}/taskList?length=10000'))
    if any(t['status'] != 'SUCCESS' for t in tasks):
        raise RuntimeError('Run ini memiliki task retry/gagal; jangan campurkan dengan benchmark normal.')
    if len(tasks) != sum(s['numCompleteTasks'] for s in chosen):
        raise RuntimeError('Data task terpotong; perkecil latihan agar seluruh metrik terbaca.')
    metric = {
        'label': label, 'seconds': seconds, 'jobs': sorted(job_ids),
        'stages': sorted(stage_ids), 'tasks': len(tasks),
        'executor_cpu_seconds': sum(s['executorCpuTime'] for s in chosen) / 1e9,
        'task_elapsed_seconds': sum(s['executorRunTime'] for s in chosen) / 1000,
        'disk_spill_bytes': sum(s['diskBytesSpilled'] for s in chosen),
        'memory_spill_bytes': sum(s['memoryBytesSpilled'] for s in chosen),
        'peak_task_execution_bytes': max(t['taskMetrics']['peakExecutionMemory'] for t in tasks),
        'shuffle_read_bytes': sum(s['shuffleReadBytes'] for s in chosen),
        'shuffle_write_bytes': sum(s['shuffleWriteBytes'] for s in chosen),
        'input_bytes': sum(s['inputBytes'] for s in chosen),
        'output_bytes': sum(s['outputBytes'] for s in chosen),
    }
    save_json(Path(out) / f'{group}.json', {'metric': metric, 'stages': chosen, 'tasks': tasks})
    return result, metric


@contextlib.contextmanager
def settings(spark, values):
    old = {key: spark.conf.get(key) for key in values}
    try:
        for key, value in values.items():
            spark.conf.set(key, str(value))
        yield
    finally:
        for key, value in old.items():
            spark.conf.set(key, value)


def plan_file(query, path):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        query.explain('formatted')
    Path(path).write_text(buffer.getvalue(), encoding='utf-8')


def summarize(records, variants):
    fields = ['seconds', 'executor_cpu_seconds', 'task_elapsed_seconds',
              'peak_task_execution_bytes', 'disk_spill_bytes', 'memory_spill_bytes',
              'shuffle_read_bytes', 'shuffle_write_bytes', 'input_bytes', 'tasks']
    result = []
    for name in variants:
        selected = [r for r in records if r['variant'] == name]
        row = {'variant': name, 'runs': len(selected), 'correct': all(r['correct'] for r in selected)}
        row.update({f'median_{key}': statistics.median(r[key] for r in selected) for key in fields})
        row['min_seconds'] = min(r['seconds'] for r in selected)
        row['max_seconds'] = max(r['seconds'] for r in selected)
        result.append(row)
    return result


def run_spill(spark, folder, rows=10000, repeats=3):
    """Window mempertahankan baris asli sambil menghitung total seluruh jendela."""
    from pyspark.sql import Window, functions as F
    out = Path(folder) / 'spill'
    out.mkdir(parents=True, exist_ok=False)
    n = min(rows, 10000)  # collect dibatasi; jangan mengumpulkan jutaan baris ke driver.
    expected_total = n * (n - 1) // 2
    variants = {'normal_buffer': 2147483647, 'forced_spill': 512}
    records = []
    # Kedua varian memakai ambang in-memory, query, data, dan partisi yang sama.
    config = {'spark.sql.adaptive.enabled': 'false', 'spark.sql.shuffle.partitions': '2',
              'spark.sql.windowExec.buffer.in.memory.threshold': '128',
              'spark.sql.windowExec.buffer.spill.threshold': '2147483647'}
    with settings(spark, config):
        def trial(name, phase):
            spark.conf.set('spark.sql.windowExec.buffer.spill.threshold', str(variants[name]))
            window = Window.orderBy('id').rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)
            query = spark.range(n, numPartitions=2).select('id', F.sum('id').over(window).alias('total'))
            plan_file(query, out / f'{name}_plan.txt')
            result, metric = measure(spark, out, f'{phase}_{name}', query.collect)
            assert len(result) == n
            assert all(row.id == i and row.total == expected_total for i, row in enumerate(result))
            metric.update(variant=name, correct=True, phase=phase)
            return metric
        for name in variants:
            trial(name, 'warmup')
        for repeat in range(repeats):
            names = list(variants)
            if repeat % 2:
                names.reverse()
            for name in names:
                records.append(trial(name, f'trial{repeat + 1}'))
    assert all(r['disk_spill_bytes'] > 0 for r in records if r['variant'] == 'forced_spill'), 'Spill belum terlihat.'
    result = {'rows': n, 'repeats': repeats, 'thresholds': variants,
              'in_memory_threshold_both': 128, 'trials': records, 'summary': summarize(records, variants),
              'limitation': 'Spill dipicu dengan konfigurasi internal Spark 4.0.1 untuk demo, bukan OOM alami atau rekomendasi produksi.'}
    save_json(out / 'result.json', result)
    return result


def file_inventory(folder):
    files = sorted(Path(folder).glob('part-*.parquet'))
    sizes = [p.stat().st_size for p in files]
    if not sizes:
        raise RuntimeError('Tidak ada file data Parquet yang ditemukan.')
    return {'files': len(files), 'total_bytes': sum(sizes), 'min_bytes': min(sizes),
            'max_bytes': max(sizes), 'average_bytes': sum(sizes) / len(sizes)}


def run_small_files(spark, folder, rows=10000, repeats=3):
    """Menulis 32 file, menggabungkannya menjadi 2 file baru, lalu membaca keduanya."""
    from pyspark.sql import functions as F
    out = Path(folder) / 'small_files'
    out.mkdir(parents=True, exist_ok=False)
    many, compact = out / 'many', out / 'compact'
    # Spark/Hadoop menerima path dengan spasi; jangan percent-encode seperti URL web.
    uri_many, uri_compact = many.resolve().as_posix(), compact.resolve().as_posix()
    expected = (rows, rows * (rows - 1) // 2, sum((i % 97 + 1) * 100 for i in range(rows)))
    with settings(spark, {'spark.sql.adaptive.enabled': 'false', 'spark.sql.shuffle.partitions': '8'}):
        source = spark.range(rows, numPartitions=4).select(
            F.col('id').alias('order_id'), ((F.col('id') % 97 + 1) * 100).alias('amount'))
        _, write_metric = measure(spark, out, 'prepare_32_files',
            lambda: source.repartition(32).write.mode('errorifexists').parquet(uri_many))
        _, compact_metric = measure(spark, out, 'compact_to_2_files',
            lambda: spark.read.parquet(uri_many).coalesce(2).write.mode('errorifexists').parquet(uri_compact))
        inventories = {'many': file_inventory(many), 'compact': file_inventory(compact)}
        assert inventories['many']['files'] == 32 and inventories['compact']['files'] == 2
        left, right = spark.read.parquet(uri_many), spark.read.parquet(uri_compact)
        # Kedua arah menjaga isi dan jumlah duplikat. Dijalankan di luar timer benchmark.
        assert left.schema == right.schema
        assert left.exceptAll(right).limit(1).count() == 0
        assert right.exceptAll(left).limit(1).count() == 0
        records = []
        def trial(name, phase):
            location = uri_many if name == 'many' else uri_compact
            def action():
                # Termasuk listing, inferensi schema Parquet, perencanaan dan action baca.
                frame = spark.read.parquet(location)
                return frame.agg(F.count('*'), F.sum('order_id'), F.sum('amount')).first()
            answer, metric = measure(spark, out, f'{phase}_read_{name}', action)
            assert tuple(answer) == expected
            metric.update(variant=name, correct=True, phase=phase)
            return metric
        for name in ('many', 'compact'):
            trial(name, 'warmup')
        for repeat in range(repeats):
            names = ['many', 'compact'] if repeat % 2 == 0 else ['compact', 'many']
            for name in names:
                records.append(trial(name, f'trial{repeat + 1}'))
        for name, location in [('many', uri_many), ('compact', uri_compact)]:
            plan_file(spark.read.parquet(location).agg(F.sum('amount')), out / f'{name}_plan.txt')
    result = {'rows': rows, 'repeats': repeats, 'inventory': inventories, 'trials': records,
              'summary': summarize(records, ['many', 'compact']), 'write_metric': write_metric,
              'compact_metric': compact_metric, 'exact_content_equal': True,
              'timer_scope': 'Membuat reader, listing/schema, merencanakan dan menjalankan agregasi. Penulisan/pemadatan diukur terpisah.'}
    save_json(out / 'result.json', result)
    return result


def write_report(spark, folder, spill, files, hourly_rate=5000.0):
    """Tarif masukan hanya simulasi rupiah per jam untuk satu mesin yang sama."""
    out = Path(folder)
    baseline, candidate = files['summary']
    b, c = baseline['median_seconds'], candidate['median_seconds']
    delta = b - c
    compaction_seconds = files['compact_metric']['seconds']
    break_even = math.ceil(compaction_seconds / delta) if delta > 0 else None
    decision = ('Kandidat dua file lebih cepat pada median run lokal ini. Uji ulang pada data representatif sebelum dipakai.'
                if delta > 0 else 'Kandidat dua file belum menghemat waktu baca pada median run ini. Jangan memilihnya hanya karena jumlah file lebih sedikit.')
    resource = {
        'baseline': baseline, 'candidate': candidate, 'hourly_rate_illustration_rupiah': hourly_rate,
        'baseline_cost_illustration': b / 3600 * hourly_rate,
        'candidate_cost_illustration': c / 3600 * hourly_rate,
        'compaction_cost_illustration': compaction_seconds / 3600 * hourly_rate,
        'read_repeats_to_recover_compaction_time': break_even,
        'speedup': b / c, 'duration_reduction_percent': delta / b * 100, 'decision': decision,
    }
    save_json(out / 'resource_comparison.json', resource)
    environment = {'python': platform.python_version(), 'spark': spark.version,
                   'java': spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
                   'master': spark.sparkContext.master, 'rows_files': files['rows'],
                   'rows_spill': spill['rows'], 'repeats': files['repeats'],
                   'application_id': spark.sparkContext.applicationId,
                   'driver_max_heap_bytes': spark.sparkContext._jvm.java.lang.Runtime.getRuntime().maxMemory(),
                   'created': datetime.now().isoformat(), 'output': str(out.resolve())}
    save_json(out / 'environment.json', environment)
    lines = ['# Spark Optimization Report', '', '## Masalah dan tujuan',
        f'Data sintetis {files["rows"]:,} transaksi tersimpan dalam 32 file kecil. Kita menguji apakah pemadatan menjadi 2 file mengurangi waktu pembacaan tanpa mengubah isi data.',
        '', '## Lingkungan dan cara mengulang',
        f'Python {environment["python"]}; Spark {environment["spark"]}; Java {environment["java"]}; {environment["master"]}. Heap maksimum JVM: {environment["driver_max_heap_bytes"]:,} byte.',
        f'Notebook utama bagian 17–20, atau dari sesi16: `python lab/spark_storage_lab.py --rows {files["rows"]} --repeats {files["repeats"]}`.',
        'Gunakan interpreter environment lab. Run baru menyimpan folder terpisah. Folder many adalah sumber; compact adalah hasil baru.',
        '', '## Hipotesis dan variabel kontrol',
        'File lebih sedikit dapat mengurangi biaya membuka file. Data, schema, codec Parquet, query, perangkat, dan versi Spark tetap sama. AQE mati. Hanya susunan file masukan yang dibandingkan dalam benchmark baca.',
        f'Satu warm-up per varian, kemudian {files["repeats"]} trial per varian dengan urutan bergantian. Median dan rentang ditampilkan. Timer baca mencakup pembuatan reader/schema dan action agregasi; penulisan serta compaction diukur terpisah.',
        'Cache Spark tidak digunakan. Cache sistem operasi tidak dikosongkan, jadi ini pengukuran pembacaan setelah pemanasan.',
        '', '## Hasil pembacaan dan penggunaan resource',
        '| Metrik | 32 file | 2 file |', '|---|---:|---:|']
    for label, key, precision in [('Median detik','median_seconds',4), ('Minimum detik','min_seconds',4),
        ('Maksimum detik','max_seconds',4), ('Median CPU task (detik)','median_executor_cpu_seconds',4),
        ('Median jumlah task','median_tasks',0), ('Median puncak memori operasi satu task (byte)','median_peak_task_execution_bytes',0),
        ('Median spill ke disk (byte)','median_disk_spill_bytes',0)]:
        lines.append(f'| {label} | {baseline[key]:.{precision}f} | {candidate[key]:.{precision}f} |')
    for label, key in [('File data','files'), ('Total ukuran Parquet (byte)','total_bytes'), ('Rata-rata ukuran file (byte)','average_bytes')]:
        lines.append(f'| {label} | {files["inventory"]["many"][key]:.0f} | {files["inventory"]["compact"][key]:.0f} |')
    lines += ['', f'Speedup: {b/c:.3f} kali. Perubahan durasi: {delta/b*100:.2f}% lebih singkat; nilai negatif berarti lebih lama.',
        'CPU task menjumlahkan waktu CPU thread task; bukan persentase CPU seluruh mesin. Puncak memori adalah maksimum peakExecutionMemory task, bukan total RAM proses. Nilai nol tidak berarti Spark tidak memakai RAM. Spill disk adalah penulisan perantara, bukan ukuran file Parquet.',
        '', '## Biaya pemadatan dan simulasi biaya uang',
        f'Pemadatan sekali: {compaction_seconds:.4f} detik (satu observasi, bukan median). Jumlah baca agar penghematan waktu menutup pemadatan: {break_even if break_even is not None else "belum ada karena kandidat tidak lebih cepat"}.',
        f'Tarif contoh Rp{hourly_rate:,.0f}/jam untuk mesin yang sama; ini asumsi latihan, bukan tarif layanan. Estimasi = durasi/3600 × tarif. Baca baseline Rp{resource["baseline_cost_illustration"]:.4f}; kandidat Rp{resource["candidate_cost_illustration"]:.4f}; pemadatan Rp{resource["compaction_cost_illustration"]:.4f}.',
        'Perhitungan ini mengabaikan waktu idle, startup, pembulatan tagihan, storage, dan jaringan. Jika mesin tetap menyala, durasi lebih singkat belum tentu mengurangi tagihan. Kapasitas CPU/RAM lebih besar perlu benchmark baru dengan tarifnya sendiri.',
        '', '## Percobaan spill',
        f'Window menghitung total seluruh id sambil mempertahankan {spill["rows"]} baris. Kedua varian memakai ambang in-memory 128 baris. Ambang spill dibandingkan: 2147483647 dan 512 baris.',
        '| Varian | Median detik | Median spill disk (byte) | Hasil benar |', '|---|---:|---:|---|']
    for row in spill['summary']:
        lines.append(f'| {row["variant"]} | {row["median_seconds"]:.4f} | {row["median_disk_spill_bytes"]:.0f} | {row["correct"]} |')
    lines += ['Konfigurasi internal ini khusus demonstrasi Spark 4.0.1. Spill sengaja dipicu; bukan bukti laptop kekurangan RAM. Tidak ada pengujian kehabisan memori. Pengaturan lama dipulihkan sesudah eksperimen.',
        '', '## Pemeriksaan hasil dan kegagalan',
        'File many dan compact dibandingkan menggunakan exceptAll dua arah: isi serta jumlah duplikat harus sama. Jumlah transaksi, jumlah order_id, dan total amount juga dibandingkan dengan rumus Python. Hasil window diperiksa satu per satu.',
        'Pada notebook utama bagian 15, satu wilayah sengaja dihilangkan dan assertion menangkap hasil yang salah. Pada modul ini, metrik hilang, task gagal, hasil berubah, atau spill demo tidak muncul akan menghentikan run; tidak diganti dengan angka nol.',
        '', '## Keputusan', decision,
        'Keputusan mempertimbangkan durasi, CPU task, ukuran file, biaya pemadatan, dan frekuensi baca. Dua file hanya parameter kelas; jangan memadatkan semua data produksi menjadi satu atau dua file.',
        '', '## Batas pengujian dan eksperimen berikutnya',
        'Data kecil pada satu mesin, tanpa jaringan MinIO, contention antar-pengguna, atau cluster terdistribusi. Tidak mengukur RAM total maupun biaya cloud aktual. Urutan bergantian mengurangi bias tetapi tidak menghilangkan pengaruh cache OS dan JVM.',
        'Ulangi pada 300.000 baris, lalu volume yang mewakili pipeline. Bandingkan beberapa ukuran file dengan partisi tanggal yang sama. Periksa skew, puncak memori task, spill, dan median/rentang. Catat juga biaya compaction dan berapa kali data dibaca.',
        '', '## Penerapan pada capstone',
        'Pada pipeline transaksi ke lake, simpan kandidat hasil pemadatan pada lokasi baru. Periksa schema, duplikasi, jumlah transaksi, dan total penjualan per tanggal sebelum mengganti input job downstream. Bandingkan waktu end-to-end termasuk penulisan. Jika hasil berubah atau SLA memburuk, gunakan kembali lokasi sumber. Latihan ini tidak mengganti data lake sungguhan.',
        '', '## Bukti yang dapat diperiksa',
        '`environment.json`, `resource_comparison.json`, `spill/result.json`, `small_files/result.json`, plan teks, serta JSON stage/task per action. JSON warmup terpisah dari trial; ringkasan hanya memakai trial.',
        '', '## Referensi',
        '- https://spark.apache.org/docs/4.0.1/monitoring.html',
        '- https://spark.apache.org/docs/4.0.1/sql-performance-tuning.html',
        '- https://github.com/apache/spark/blob/v4.0.1/sql/catalyst/src/main/scala/org/apache/spark/sql/internal/SQLConf.scala', '']
    (out / 'Spark_Optimization_Report.md').write_text('\n'.join(lines), encoding='utf-8')
    return resource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--hourly-rate', type=float, default=5000, help='Tarif simulasi, rupiah/jam.')
    parser.add_argument('--hold-ui', action='store_true')
    args = parser.parse_args()
    if not 1000 <= args.rows <= 1000000 or not 1 <= args.repeats <= 10 or not math.isfinite(args.hourly_rate) or args.hourly_rate < 0:
        parser.error('rows 1000–1000000, repeats 1–10, hourly-rate harus angka hingga >= 0.')
    import pyspark
    if pyspark.__version__ != '4.0.1':
        parser.error('Gunakan PySpark 4.0.1 sesuai requirements.txt.')
    java = shutil.which('java')
    if not java:
        parser.error('Java 17 belum ditemukan pada PATH.')
    probe = subprocess.run([java, '-XshowSettings:properties', '-version'], capture_output=True, text=True, timeout=20)
    info = probe.stdout + probe.stderr
    home = re.search(r'^\s*java.home\s*=\s*(.+)$', info, re.MULTILINE)
    major = re.search(r'^\s*java.specification.version\s*=\s*(\d+)', info, re.MULTILINE)
    if not home or not major or int(major.group(1)) < 17:
        parser.error('Java 17+ diperlukan.')
    os.environ.update(SPARK_HOME=str(Path(pyspark.__file__).resolve().parent), JAVA_HOME=home.group(1).strip(),
                      SPARK_LOCAL_IP='127.0.0.1', PYSPARK_PYTHON=sys.executable)
    from pyspark.sql import SparkSession
    out = Path(__file__).resolve().parent / 'outputs' / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_storage_' + uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    spark = (SparkSession.builder.master('local[2]').appName('Sesi16-Spill-SmallFiles')
             .config('spark.ui.bindAddress','127.0.0.1').config('spark.driver.host','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    print('Spark UI:', spark.sparkContext.uiWebUrl, flush=True)
    print('Folder hasil:', out, flush=True)
    try:
        spill = run_spill(spark, out, args.rows, args.repeats)
        print('Spill selesai; hasil setiap trial sama.', flush=True)
        files = run_small_files(spark, out, args.rows, args.repeats)
        print('Small files selesai; isi 32 file dan 2 file sama.', flush=True)
        report = write_report(spark, out, spill, files, args.hourly_rate)
        print(report['decision'], flush=True)
        save_json(out / 'verification.json', {'completed': True, 'spill_observed': True,
            'exact_content_equal': files['exact_content_equal'], 'measured_trials': 4 * args.repeats})
        if args.hold_ui:
            input('Tekan Enter untuk menutup Spark UI.')
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
