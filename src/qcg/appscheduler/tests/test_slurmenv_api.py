import pytest
import tempfile

from os.path import join, abspath, exists
from shutil import rmtree
from pathlib import Path

from qcg.appscheduler.slurmres import in_slurm_allocation, get_num_slurm_nodes

from qcg.appscheduler.tests.utils import get_slurm_resources_binded, set_pythonpath_to_qcg_module, find_single_aux_dir
from qcg.appscheduler.api.manager import LocalManager
from qcg.appscheduler.api.job import Jobs
from qcg.appscheduler.api.errors import ConnectionError
from qcg.appscheduler.api.jobinfo import JobInfo

from qcg.appscheduler.tests.utils import SHARED_PATH


def test_slurmenv_api_resources():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})
        api_res = m.resources()

        assert all(('totalNodes' in api_res, 'totalCores' in api_res))
        assert all((api_res['totalNodes'] == resources.totalNodes, api_res['totalCores'] == resources.totalCores))

        aux_dir = find_single_aux_dir(str(tmpdir))

        assert all((exists(join(tmpdir, '.qcgpjm-client', 'api.log')),
                    exists(join(aux_dir, 'service.log'))))

    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)


def test_slurmenv_api_submit_simple():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs().\
            addStd({ 'name': 'host',
                     'execution': {
                         'exec': '/bin/hostname',
                         'args': [ '--fqdn' ],
                         'stdout': 'std.out',
                         'stderr': 'std.err'
                     }})
        assert submitWaitInfo(m, jobs, 'SUCCEED')
    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)


def test_slurmenv_api_submit_many_cores():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs(). \
            addStd({ 'name': 'host',
                     'execution': {
                         'exec': '/bin/hostname',
                         'args': [ '--fqdn' ],
                         'stdout': 'out',
                     },
                     'resources': { 'numCores': { 'exact': resources.totalCores } }
                     })
        jinfos = submitWaitInfo(m, jobs, 'SUCCEED')

        # check working directories of job's inside working directory of service
        assert tmpdir == jinfos['host'].wdir, str(jinfos['host'].wdir)
        assert all((len(jinfos['host'].nodes) == resources.totalNodes,
                    jinfos['host'].totalCores == resources.totalCores)), str(jinfos['host'])

    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)


def submitWaitInfo(manager, jobs, expected_status):
    ids = manager.submit(jobs)
    assert len(ids) == len(jobs.jobNames())

    manager.wait4all()
    jinfos = manager.infoParsed(ids)

    # check # of jobs is correct
    assert len(jinfos) == len(ids)
    # check expected jobs status
    assert all(jid in jinfos and jinfos[jid].status == expected_status for jid in ids)

    return jinfos


def test_slurmenv_api_submit_resource_ranges():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs(). \
            addStd({ 'name': 'host',
                     'execution': {
                         'exec': '/bin/hostname',
                         'args': [ '--fqdn' ],
                         'stdout': 'out',
                     },
                     'resources': { 'numCores': { 'min': 1 } }
                     })
        # job should faile because of missing 'max' parameter
        jinfos = submitWaitInfo(m, jobs, 'FAILED')
        jinfo = jinfos['host']
        assert "Both core's range boundaries (min, max) must be defined" in jinfo.messages, str(jinfo)

        jobs = Jobs(). \
            addStd({ 'name': 'host2',
                     'execution': {
                         'exec': '/bin/hostname',
                         'args': [ '--fqdn' ],
                         'stdout': 'out',
                     },
                     'resources': {
                         'numNodes': { 'exact': 1 },
                         'numCores': { 'min': 1, 'max': resources.nodes[0].total + 1 } }
                     })
        # job should run on single node (the first free) with all available cores
        jinfos = submitWaitInfo(m, jobs, 'SUCCEED')
        jinfo = jinfos['host2']
        assert all((len(jinfo.nodes) == 1, jinfo.totalCores == resources.nodes[0].total)), str(jinfo)

        jobs = Jobs(). \
            addStd({ 'name': 'host3',
                     'execution': {
                         'exec': '/bin/hostname',
                         'args': [ '--fqdn' ],
                         'stdout': 'out',
                     },
                     'resources': {
                         'numCores': { 'min': 1, 'max': resources.nodes[0].total + 1 } }
                     })
        # job should run on at least two nodes with total maximum given cores
        jinfos = submitWaitInfo(m, jobs, 'SUCCEED')
        jinfo = jinfos['host3']
        assert all((len(jinfo.nodes) == 2, jinfo.totalCores == resources.nodes[0].total + 1)), str(jinfo)

    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
#        rmtree(tmpdir)


def test_slurmenv_api_submit_exceed_total_cores():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs(). \
            addStd({ 'name': 'date',
                     'execution': { 'exec': '/bin/date' },
                     'resources': {
                         'numCores': { 'exact': resources.totalCores + 1 }
                     }})
        with pytest.raises(ConnectionError, match=r".*Not enough resources.*"):
            m.submit(jobs)
        assert len(m.list()) == 0

        jobs = Jobs(). \
        addStd({ 'name': 'date',
                     'execution': { 'exec': '/bin/date' },
                     'resources': {
                         'numNodes': { 'exact': resources.totalNodes + 1 }
                     }})
        with pytest.raises(ConnectionError, match=r".*Not enough resources.*"):
            ids = m.submit(jobs)
        assert len(m.list()) == 0

        jobs = Jobs(). \
            addStd({ 'name': 'date',
                     'execution': {
                         'exec': '/bin/date',
                         'stdout': 'std.out',
                     },
                     'resources': { 'numCores': { 'exact': resources.totalCores  } }
                     })
        jinfos = submitWaitInfo(m, jobs, 'SUCCEED')
        assert jinfos['date'].totalCores == resources.totalCores
    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)


def test_slurmenv_api_std_streams():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs(). \
            addStd({ 'name': 'host',
                     'execution': {
                         'exec': 'cat',
                         'stdin': '/etc/system-release',
                         'stdout': 'out',
                         'stderr': 'err'
                     }})
        assert submitWaitInfo(m, jobs, 'SUCCEED')

        assert all((exists(join(tmpdir, 'out')), exists(join(tmpdir, 'err'))))

        with open(join(tmpdir, 'out'), 'rt') as out_f:
            out = out_f.read()

        with open(join('/etc/system-release'), 'rt') as sr_f:
            system_release = sr_f.read()

        assert system_release in out
    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)


def test_slurmenv_api_std_streams_many_cores():
    if not in_slurm_allocation() or get_num_slurm_nodes() < 2:
        pytest.skip('test not run in slurm allocation or allocation is smaller than 2 nodes')

    resources, allocation = get_slurm_resources_binded()

    set_pythonpath_to_qcg_module()
    tmpdir = str(tempfile.mkdtemp(dir=SHARED_PATH))

    try:
        m = LocalManager(['--log', 'debug', '--wd', tmpdir, '--report-format', 'json'], {'wdir': str(tmpdir)})

        jobs = Jobs(). \
            addStd({ 'name': 'host',
                     'execution': {
                         'exec': 'cat',
                         'stdin': '/etc/system-release',
                         'stdout': 'out',
                         'stderr': 'err'
                     },
                     'resources': {
                         'numCores': { 'exact': 2 }
                     }
                     })
        assert submitWaitInfo(m, jobs, 'SUCCEED')

        assert all((exists(join(tmpdir, 'out')), exists(join(tmpdir, 'err'))))

        with open(join(tmpdir, 'out'), 'rt') as out_f:
            out = out_f.read()

        with open(join('/etc/system-release'), 'rt') as sr_f:
            system_release = sr_f.read()

        assert system_release in out
    finally:
        if m:
            m.finish()
            m.stopManager()
            m.cleanup()
        rmtree(tmpdir)
