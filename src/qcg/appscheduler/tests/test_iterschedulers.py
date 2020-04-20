import pytest

from qcg.appscheduler.iterscheduler import IterScheduler, MaximumIters, SplitInto, DEFAULT_SCHEDULER


def test_iterscheduler_parsing():
    assert IterScheduler.GetScheduler('maximum-iters') == MaximumIters
    assert IterScheduler.GetScheduler('MAXIMUM-ITERS') == MaximumIters
    assert IterScheduler.GetScheduler('Maximum-Iters') == MaximumIters
    assert IterScheduler.GetScheduler('split-into') == SplitInto
    assert IterScheduler.GetScheduler('SPLIT-INTO') == SplitInto
    assert IterScheduler.GetScheduler('SpliT-Into') == SplitInto
    assert IterScheduler.GetScheduler('unknown') == DEFAULT_SCHEDULER


def test_iterscheduler_splitinto():
    iters = 10

    resources = 10
    split_into = 10
    si_sched_gen = IterScheduler.GetScheduler('split-into')({'min': 1}, iters, resources, parts=split_into).generate()
    for i in range(iters):
        job_iter_res = next(si_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == resources / iters)),\
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(si_sched_gen)

    resources = 10
    split_into = 5
    si_sched_gen = IterScheduler.GetScheduler('split-into')({'min': 1}, iters, resources, parts=split_into).generate()
    for i in range(iters):
        job_iter_res = next(si_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == resources / split_into)),\
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(si_sched_gen)

    resources = 10
    split_into = 2
    si_sched_gen = IterScheduler.GetScheduler('split-into')({'min': 1}, iters, resources, parts=split_into).generate()
    for i in range(iters):
        job_iter_res = next(si_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == resources / split_into)), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(si_sched_gen)

    # default 'parts' as number of iterations
    resources = 10
    si_sched_gen = IterScheduler.GetScheduler('split-into')({'min': 1}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(si_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == resources / iters)), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(si_sched_gen)

def test_iterscheduler_maximum_iters():
    # all iterations in single round
    iters = 10
    resources = 10
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 1, }, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == 1)), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # two rounds
    iters = 20
    resources = 10
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 1, }, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == 1)), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # single rounds, with two resources
    iters = 5
    resources = 10
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 1, }, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == 2)), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # single rounds, 4, 3, 3
    iters = 3
    resources = 10
    res = [4, 3, 3]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 1, }, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == res[i])), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # single rounds, 4, 3, 3
    iters = 3
    resources = 10
    res = [4, 3, 3]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == res[i])), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # single rounds, 4, 4, 3
    iters = 3
    resources = 11
    res = [4, 4, 3]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 1, job_iter_res['max'] == res[i])), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # single rounds, 4, 4, 3
    iters = 3
    resources = 11
    res = [4, 4, 3]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 3}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 3, job_iter_res['max'] == res[i])), \
            str(job_iter_res)
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # two rounds (two jobs in first, single in second), 6, 5, 11
    iters = 3
    resources = 11
    res = [6, 5, 11]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 5}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 5, job_iter_res['max'] == res[i])), \
            "{} - {}".format(i, str(job_iter_res))
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # two rounds (2 jobs in single), 6, 5, 6, 5
    iters = 4
    resources = 11
    res = [6, 5, 6, 5]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 5}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 5, job_iter_res['max'] == res[i])), \
            "{} - {}".format(i, str(job_iter_res))
    with pytest.raises(StopIteration):
        next(mi_sched_gen)

    # four rounds (1 job in round), 11, 11, 11, 11
    iters = 4
    resources = 11
    res = [11, 11, 11, 11]
    mi_sched_gen = IterScheduler.GetScheduler('maximum-iters')({'min': 6}, iters, resources).generate()
    for i in range(iters):
        job_iter_res = next(mi_sched_gen)
        assert job_iter_res and all(('max' in job_iter_res, 'min' in job_iter_res,
                                     job_iter_res['min'] == 6, job_iter_res['max'] == res[i])), \
            "{} - {}".format(i, str(job_iter_res))
    with pytest.raises(StopIteration):
        next(mi_sched_gen)
