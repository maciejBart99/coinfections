import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

from order import DB


@dataclass
class TaskData:
    order_id: int
    file_1: str
    file_2: str
    positions: List[int]


THREADS_COUNT = 1
EXECUTOR = ThreadPoolExecutor(THREADS_COUNT)
PRIMERS_PATH = 'resources/primersNC.bed'
REFERENCE_PATH = 'resources/covid_reference.fa'
GATK_PATH = os.environ.get('GATK_PATH')
WORK_DIR = 'wd'


def pipeline(data: TaskData) -> str:
    pipeline_id = str(uuid.uuid4())

    if not os.path.exists(WORK_DIR):
        os.mkdir(WORK_DIR)

    os.system(f'bwa index -a bwtsw {REFERENCE_PATH} -p myref')

    f_1 = f'{os.path.join(WORK_DIR, pipeline_id)}_1.fastaq.gz'
    f_2 = f'{os.path.join(WORK_DIR, pipeline_id)}_2.fastaq.gz'
    os.system(f'cp {data.file_1} {f_1}')
    os.system(f'cp {data.file_2} {f_2}')

    res_1 = f'{os.path.join(WORK_DIR, pipeline_id)}_clfm.bam'
    os.system(f'bwa mem -t4 {REFERENCE_PATH} {f_1} {f_2} '
              f'| samtools ampliconclip --strand --fail --fail-len 10 -b {PRIMERS_PATH} - '
              f'| samtools fixmate -O bam,level=1 - {res_1}')

    res_2 = f'{os.path.join(WORK_DIR, pipeline_id)}_clfmrg.bam'
    os.system(f'{GATK_PATH} --java-options "-Xmx4g" AddOrReplaceReadGroups --VALIDATION_STRINGENCY LENIENT '
              f'-I {res_1} -O {res_2} -LB lib1 -PL ILLUMINA -PU unit1 -SM {pipeline_id}')

    res_3 = f'{os.path.join(WORK_DIR, pipeline_id)}_clfmrgs.bam'
    os.system(f'samtools sort -T tmp_samtools -o {res_3} {res_2}')

    os.system(f'samtools index {res_3}')

    p_min = min(data.positions)
    p_max = max(data.positions)

    res_4 = f'{os.path.join(WORK_DIR, pipeline_id)}_clfmrgs_narrowed.bam'
    os.system(f'samtools view -b -o {res_4} {res_3} NC_045512.2:{p_min}-{p_max}')
    os.system(f'samtools index {res_4}')

    os.remove(res_1)
    os.remove(res_2)
    os.remove(f_1)
    os.remove(f_2)
    os.remove(res_3)
    os.remove(data.file_1)
    os.remove(data.file_2)

    res_5 = f'{os.path.join("results", pipeline_id)}.txt'
    os.system(f'python3 check_variants.py {res_4} {",".join([str(x) for x in data.positions])} {res_5}')

    os.remove(res_4)

    return res_5


def task(data: TaskData):
    session = DB()
    logging.info(f"Starting pipeline {data.order_id}...")

    session.execute(f"UPDATE orders SET state = 'IN_PROGRESS' WHERE id = '{data.order_id}'")
    session.commit()
    try:
        result = pipeline(data)
        logging.info(f"Pipeline finished {data.order_id}...")
        session.execute(f"UPDATE orders SET state = 'READY', result_path = '{result}' WHERE id = '{data.order_id}'")
        session.commit()
    except Exception as ex:
        logging.error(str(ex))
        session.execute(f"UPDATE orders SET state = 'FAILED' WHERE id = '{data.order_id}'")
        session.commit()


def send_task(file_1: str, file_2: str, order_id: int, positions: List[int]):
    EXECUTOR.submit(task, TaskData(order_id, file_1, file_2, positions))
