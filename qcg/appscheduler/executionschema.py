import os
import logging

from qcg.appscheduler.errors import *


class ExecutionSchema:

    @classmethod
    def GetSchema(cls, name, config):
        if name not in __SCHEMAS__:
            raise InternalError('Invalid execution schema name: %s' % name)

        return __SCHEMAS__[name](config)

    def __init__(self):
        pass

    def preprocess(self, exJob):
        pass


class SlurmExecution(ExecutionSchema):
    EXEC_NAME = 'slurm'

    def __init__(self, config):
        super(SlurmExecution, self).__init__()

    def __mergePerNodeSpec(self, strList):
        prev_value = None
        result = [ ]
        n = 1

        for t in strList.split(','):
            if prev_value is not None:
                if prev_value == t:
                    n += 1
                else:
                    if n > 1:
                        result.append("%s(x%d)" % (prev_value, n))
                    else:
                        result.append(prev_value)

                    prev_value = t
                    n = 1
            else:
                prev_value = t
                n = 1

        if prev_value is not None:
            if n > 1:
                result.append("%s(x%d)" % (prev_value, n))
            else:
                result.append(prev_value)

        return ','.join([str(el) for el in result])


    def __checkSameCores(self, tasksList):
        same = None

        for t in tasksList.split(','):
            if same is not None:
                if t != same:
                    return None
            else:
                same = t

        return same


    def preprocess(self, exJob):
        merged_tasks_per_node = self.__mergePerNodeSpec(exJob.tasks_per_node)

        exJob.env.update({
            'SLURM_NNODES': str(exJob.nnodes),
            'SLURM_NODELIST': exJob.nlist,
            'SLURM_NPROCS': str(exJob.ncores),
            'SLURM_NTASKS': str(exJob.ncores),
            'SLURM_JOB_NODELIST': exJob.nlist,
            'SLURM_JOB_NUM_NODES': str(exJob.nnodes),
            'SLURM_STEP_NODELIST': exJob.nlist,
            'SLURM_STEP_NUM_NODES': str(exJob.nnodes),
            'SLURM_STEP_NUM_TASKS': str(exJob.ncores),
            'SLURM_JOB_CPUS_PER_NODE': merged_tasks_per_node,
            'SLURM_STEP_TASKS_PER_NODE': merged_tasks_per_node,
            'SLURM_TASKS_PER_NODE': merged_tasks_per_node 
        })

        same_cores = self.__checkSameCores(exJob.tasks_per_node)
        if same_cores is not None:
            exJob.env.update({ 'SLURM_NTASKS_PER_NODE': same_cores })

        # create host file
        hostfile = os.path.join(exJob.wdPath, ".%s.hostfile" % exJob.job.name)
        with open(hostfile, 'w') as f:
            for node in exJob.allocation.nodeAllocations:
                for i in range(0, node.cores):
                    f.write("%s\n" % node.node.name)

        exJob.env.update({
            'SLURM_HOSTFILE': hostfile
        })

        job_exec = exJob.jobExecution.exec
        job_args = exJob.jobExecution.args

        # create run configuration
        runConfFile = os.path.join(exJob.wdPath, ".%s.runconfig" % exJob.job.name)
        with open(runConfFile, 'w') as f:
            f.write("0\t%s %s\n" % (
                job_exec,
                ' '.join('{0}'.format(str(arg).replace(" ", "\ ")) for arg in job_args)))
            if exJob.ncores > 1:
                if exJob.ncores > 2:
                    f.write("1-%d /bin/true\n" % (exJob.ncores - 1))
                else:
                    f.write("1 /bin/true\n")

        #        exJob.modifiedArgs = [ "-n", str(exJob.ncores), "--export=NONE", "-m", "arbitrary", "--multi-prog", runConfFile ]
        #        exJob.modifiedArgs = [ "-n", str(exJob.ncores), "-m", "arbitrary", "--mem-per-cpu=0", "--slurmd-debug=verbose", "--multi-prog", runConfFile ]

        exJob.jobExecution.exec = 'srun'
        exJob.jobExecution.args = [
            "-n", str(exJob.ncores),
            "-m", "arbitrary",
            "--mem-per-cpu=0",
            "--multi-prog" ]

        if exJob.job.resources.wt:
            exJob.jobExecution.args.extend(["--time", "0:{}".format(int(exJob.job.resources.wt.total_seconds()))])

        exJob.jobExecution.args.append(runConfFile)


class DirectExecution(ExecutionSchema):
    EXEC_NAME = 'direct'

    def __init__(self, config):
        super(DirectExecution, self).__init__()

    def preprocess(self, exJob):
        pass


__SCHEMAS__ = {
    SlurmExecution.EXEC_NAME: SlurmExecution,
    DirectExecution.EXEC_NAME: DirectExecution
}
